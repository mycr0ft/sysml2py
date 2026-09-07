#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cameo-style state-machine simulation (MVP).

Builds an executable state machine from a parsed SysML v2 model and
drives it: triggers fire transitions, guards are evaluated for real
against the model's attribute values (pint-aware, via
:mod:`sysmlpy.evaluator`), and effects are logged as text.

    from sysmlpy import loads
    from sysmlpy.sim import StateSimulator

    sim = StateSimulator(model, focus="Cruise")
    sim.send("Engage")          # fire a signal trigger
    sim.state                   # -> 'engaged'
    sim.available()             # [(trigger, guard_text, passes_now)]
    sim.set_value("speed", 70)  # what-if on guard variables
    sim.step()                  # fire the first enabled transition
    sim.log                     # history of fired/blocked transitions

Command line: ``sysmlpy sim FILE [--focus NAME] [--set NAME=VALUE]
[--run "Sig1; Sig2"]`` (see ``cmd_sim`` in ``__main__.py``) for an
interactive TUI showing the live state and the transitions available
from it.

Execution is delegated to the optional ``transitions`` library (the
``sim`` extra: ``poetry install -E sim`` / ``pip install
sysmlpy[sim]``).  Library choice: ``transitions`` (pytransitions)
builds machines from *data* at runtime (``Machine(model=…, states=[…],
transitions=[{...}])``), which is exactly the shape of the
SysML-model → machine bridge, and its guards (``conditions``) and
effects (``before``/``after``) map 1:1 onto the SysML guard/effect
features.  The runner-up, ``python-statemachine``, prefers declarative
class definitions, which is awkward for arbitrary parsed models.

Scope of this MVP (deliberate cuts, tracked in TODO.md):

- composite regions expand flat with qualified names
  (``Composite.Sub``): entering a composite lands in its initial
  substate, the region runs its own transitions, and transitions
  declared on the composite apply from every substate (UML
  composite transitions; deeper transitions win the fall-through).
  Substates referenced by bare name from outside their region are
  still flattened implicitly
- one machine per simulator (``focus`` picks which); parallel regions
  (``state def C parallel { ... }`` — root-level or inside a
  composite) simulate as co-active regions (v0.89.0): entering the
  composite activates every region at its default entry, each region
  fires its own transitions independently (the event is dispatched to
  each region in declaration order), and a transition out of the
  composite (or to another region) exits/re-enters all regions;
  ``sim.state`` is a tuple of the active leaves while regions are
  co-active
- assignment effects (``do x := 5``) execute against the simulator's
  values (:meth:`StateSimulator.set_value`), so guards evaluated later
  see the new value; other effects (``do <action>``, ``send``) are
  logged only
- history pseudostates (``state h : HistoryUsage;``/``h :
  HistoryUsage;``, or ``h;``/``history;`` by name convention) are
  honored: a transition targeting one re-enters the region's last
  active substate.  Deep history restores the deepest visited state
  when ``deep_history=True`` is passed to :class:`StateSimulator` —
  the language has no deep-history form, so it is a simulator option
- completion transitions (no ``accept`` trigger) fire automatically on
  entering a state (run-to-completion), and manually via
  :meth:`StateSimulator.step`
"""

from __future__ import annotations

import re
import time
from typing import Any, Dict, List, NamedTuple, Optional, Tuple

from sysmlpy.antlr_parser import SysMLSyntaxError  # noqa: F401 (re-export)
from sysmlpy.evaluator import (
    EvaluationError,
    _expression_text,
    collect_values,
    evaluate_expression,
)

try:
    from transitions import Machine
except ImportError as _e:  # pragma: no cover - only without the extra
    raise ImportError(
        "State-machine simulation needs the optional 'transitions' "
        "library: pip install sysmlpy[sim] (poetry: poetry install "
        "-E sim)") from _e

__all__ = [
    "SimulationError",
    "TransitionSpec",
    "StepRecord",
    "StateSimulator",
    "build_state_machine",
    "run_tui",
]


class SimulationError(Exception):
    """The requested state machine cannot be simulated as asked."""


# ---------------------------------------------------------------------------
# Extraction: parsed model -> machine descriptors (guards, effects included)
# ---------------------------------------------------------------------------

def _as_list(value: Any) -> List[Any]:
    """Normalize grammar dict memberships: dict OR list OR None."""
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _walk_named(node: Any, target: str):
    """Yield every dict named *target* anywhere under *node*."""
    if isinstance(node, dict):
        if node.get("name") == target:
            yield node
        for v in node.values():
            yield from _walk_named(v, target)
    elif isinstance(node, list):
        for item in node:
            yield from _walk_named(item, target)


def _qualified_name_leaf(node: Any) -> Optional[str]:
    """Last name of the first QualifiedName under *node* (or None)."""
    for qn in _walk_named(node, "QualifiedName"):
        names = qn.get("names")
        if isinstance(names, list) and names:
            return names[-1]
    return None


def _payload_trigger_guard(trigger_member: dict) -> tuple:
    """Recover ``(trigger_name, guard_text)`` from a TriggerActionMember.

    In the ``accept <Sig> [when <expr>]`` shorthand both the trigger
    name and its guard live inside the single TriggerActionMember::

        TriggerAction -> AcceptParameterPart -> PayloadParameterMember
        -> PayloadParameter

    The payload's ``identification.declaredName`` is the trigger signal
    name.  Its guard expression tree lives in ``PayloadParameter.tvp``
    (TriggerValuePart) -> TriggerExpression with ``kind.isWhen`` set.
    (The boxes-view's generic QualifiedName search trips over the
    guard here: ``accept Engage when key`` was reported as trigger
    ``key`` — the guard's own feature name.)
    """
    trigger_action = trigger_member.get("ownedRelatedElement") or {}
    part = trigger_action.get("part") or {}
    for part_rel in _as_list(part.get("ownedRelationship")):
        if part_rel.get("name") != "PayloadParameterMember":
            continue
        payload = part_rel.get("ownedRelatedElement") or {}
        ident = payload.get("identification") or {}
        trigger = ident.get("declaredName")
        guard = None
        tvp = payload.get("tvp") or {}
        for tfv in _as_list(tvp.get("ownedRelationship")):
            trigger_expr = tfv.get("ownedRelatedElement") or {}
            if trigger_expr.get("name") != "TriggerExpression":
                continue
            kind = trigger_expr.get("kind") or {}
            if not kind.get("isWhen"):
                continue
            for oem in _as_list(trigger_expr.get("ownedRelationship")):
                expr = (oem.get("ownedRelatedElement") or {}).get(
                    "expression")
                if expr:
                    guard = _expression_text(expr) or _qualified_name_leaf(
                        expr)
        return trigger, guard
    return None, None


def _effect_text(effect_member: dict) -> Optional[str]:
    """Recover a readable effect name/text from an EffectBehaviorMember."""
    node = effect_member.get("memberElement") or effect_member.get(
        "ownedRelatedElement") or {}
    if not isinstance(node, dict):
        return None
    for expr in _walk_named(node, "OwnedExpression"):
        text = _expression_text(expr.get("expression") or expr)
        if text:
            return text
    return _qualified_name_leaf(node)


class TransitionSpec(NamedTuple):
    """One transition, fully resolved for execution."""

    name: Optional[str]
    source: str
    target: str
    #: Signal name (``accept <Sig>``), or None for a completion
    #: transition (fires by run-to-completion).
    trigger: Optional[str]
    #: Guard expression text (``when <expr>``), or None.
    guard: Optional[str]
    #: Effect action name (``do <action>``), or None.
    effect: Optional[str]
    #: For transitions targeting a history pseudostate: the flat name
    #: of the region whose history the target remembers (``""`` =
    #: machine root).  None for ordinary transitions.
    history_region: Optional[str] = None
    #: For transitions whose target is a parallel composite: the flat
    #: name of the composite whose regions all activate on entry
    #: (v0.89.0).  None otherwise.
    enters_parallel: Optional[str] = None
    #: For transitions whose source lies inside a parallel composite
    #: but whose target is outside it: firing exits every region of
    #: that composite (v0.89.0).  None otherwise.
    exits_parallel: Optional[str] = None


#: Assignment-effect shape: ``name := expression`` (SysML assignment
#: operator; the effect text from the collector renders exactly this).
_ASSIGNMENT_RE = re.compile(r"^\s*([\w.]+)\s*:=\s*(.+?)\s*$", re.S)


def _mangle(name: str) -> str:
    """Sanitize a SysML name into a pytransitions event identifier."""
    return re.sub(r"\W", "_", name) or "anon"


class MachineDescriptor(NamedTuple):
    """Flat view of one ``state def`` machine, ready for simulation."""

    name: Optional[str]
    states: List[str]
    initial: str
    transitions: List[TransitionSpec]
    #: Notes gathered during extraction (fallbacks taken, etc.).
    notes: List[str]
    #: Transitions whose endpoints could not be resolved to states —
    #: excluded from simulation but surfaced for diagnostics (the
    #: validator turns these into UNRESOLVED_TRANSITION_ENDPOINT).
    skipped: Tuple[TransitionSpec, ...] = ()
    #: History pseudostate markers: flat marker name -> flat name of
    #: the region whose last active substate it remembers (``""`` =
    #: machine root).
    history_markers: Dict[str, str] = {}
    #: Region flat name -> default entry (initial substate leaf);
    #: includes ``""`` -> machine initial.  Fallback when no history
    #: has been recorded yet.
    region_defaults: Dict[str, str] = {}
    #: Parallel composite flat name (``""`` = machine root) -> the
    #: flat names of its direct regions, in declaration order (v0.89.0).
    #: All of these are active simultaneously while the composite is
    #: entered; the tracked leaf per region is its default entry
    #: (``region_defaults``).
    parallel_regions: Dict[str, Tuple[str, ...]] = {}
    #: Parallel composite -> its enclosing parallel composite (or
    #: ``""`` when at the machine root) — the cascade order for
    #: enter/exit bookkeeping (v0.89.0).
    parallel_parent: Dict[str, str] = {}


def build_state_machine(model, focus: Optional[str] = None,
                        _collect=None) -> MachineDescriptor:
    """Extract the (first / focus) state machine of *model*.

    Reuses the boxes-view machine collector (states, initial,
    composites — battle-tested by the stv boxes tests) and enriches its
    transitions with shorthand-form guards (``accept <Sig> when
    <expr>``) and effects (``do <action>``) which that collector
    reports as ``None``.
    """
    if _collect is None:
        from sysmlpy.boxes_view import _collect_state_machine as _collect
    visit = load_model_grammar(model)
    machines = _collect(visit)
    if focus is not None:
        machines = [m for m in machines if m.get("name") == focus]
        if not machines:
            known = [m.get("name") for m in _collect(visit)]
            raise SimulationError(
                f"No state machine named {focus!r}; found {known}")
    if not machines:
        raise SimulationError(
            "The model contains no state machine (no 'state def' / "
            "'state' with a body).")
    sm = machines[0]
    notes: List[str] = []

    # Parallel composites are supported (v0.89.0): ``state def C
    # parallel { ... }`` (or ``state c parallel { ... }``) makes the
    # direct substates co-active regions.  ``parallel_regions`` maps
    # the composite's flat name (``""`` = machine root) to the default
    # entry leaf of each region, in declaration order.
    parallel_regions: Dict[str, Tuple[str, ...]] = {}
    if sm.get("parallel"):
        notes.append(
            f"machine {sm.get('name')!r} declares parallel regions; "
            "the top-level states are co-active")

    def _state_name(s):
        return s["name"] if isinstance(s, dict) else s

    def _has_region(s):
        return isinstance(s, dict) and (s.get("states") or
                                        s.get("composites"))

    # Composite regions are expanded flat with qualified names
    # (``Composite.Sub``, ``Composite.Inner.Deep``):
    #   - a transition targeting a composite enters its initial
    #     substate (UML default entry),
    #   - a transition declared *on* a composite applies in every
    #     substate (UML composite transition), emitted after the
    #     region's own transitions so deeper transitions win the
    #     fall-through,
    #   - a composite declaring ``parallel`` activates all of its
    #     direct regions simultaneously (v0.89.0).
    states: List[str] = []
    raw: List[dict] = []
    # history pseudostate markers: flat marker name -> region flat name
    markers_flat: Dict[str, str] = {}
    # region flat name -> default entry (filled during expansion; the
    # machine root is filled after the initial-state resolution below)
    region_defaults_flat: Dict[str, str] = {}

    def _expand_region(level, prefix, all_names):
        local_flat: Dict[str, str] = {}
        entry_of: Dict[str, str] = {}
        substates_of: Dict[str, List[str]] = {}

        for s in level.get("states", []):
            nm = _state_name(s)
            if nm is None:
                continue
            if _has_region(s):
                flat_prefix = prefix + nm + "."
                inner_flat, inner_entry, inner_subs = _expand_region(
                    s, flat_prefix, all_names)
                init = s.get("initial")
                entry = None
                if init:
                    entry = inner_flat.get(init) or inner_entry.get(init)
                    if entry is None:
                        notes.append(
                            f"composite {nm!r}: initial {init!r} not "
                            "found; entering at the first substate")
                if entry is None:
                    entry = next(iter(inner_flat.values()), None)
                    if entry is None:
                        # v0.89.0: every direct child is itself a
                        # composite (e.g. parallel regions) — fall back
                        # to the first child composite's default entry
                        # instead of demoting the whole composite to a
                        # leaf
                        entry = next(iter(inner_entry.values()), None)
                if entry is None:
                    # region without simulating states: a leaf
                    flat = prefix + nm
                    states.append(flat)
                    local_flat[nm] = flat
                    substates_of[nm] = [flat]
                    continue
                entry_of[nm] = entry
                region_defaults_flat[prefix + nm] = entry
                if isinstance(s, dict) and s.get("parallel"):
                    # v0.89.0: all direct regions co-active — the
                    # descriptor records the region FLAT NAMES (the
                    # tracked leaf per region is its default entry,
                    # resolved via region_defaults at activation time)
                    region_leaves = []
                    region_names = []
                    for child in s.get("states", []):
                        cn = _state_name(child)
                        if cn is None:
                            continue
                        region_flat = prefix + nm + "." + cn
                        if _has_region(child):
                            cl = region_defaults_flat.get(region_flat)
                            if cn in inner_entry:
                                cl = cl or inner_entry.get(cn)
                            if cl:
                                region_leaves.append(cl)
                                region_names.append(region_flat)
                        elif cn in inner_flat:
                            region_leaves.append(inner_flat[cn])
                            region_names.append(region_flat)
                    if len(region_leaves) > 1:
                        parallel_regions[prefix + nm] = tuple(region_names)
                        notes.append(
                            f"composite {prefix + nm!r} declares parallel "
                            f"regions; {len(region_leaves)} co-active regions")
                    # composite-level transitions are available from
                    # every leaf under the composite (not just the
                    # direct children) so region exits work from any
                    # depth
                    sub_prefix = prefix + nm + "."
                    substates_of[nm] = [x for x in states
                                        if x.startswith(sub_prefix)]
                else:
                    substates_of[nm] = (list(inner_flat.values()) +
                                        list(inner_entry.values()))
            else:
                flat = prefix + nm
                states.append(flat)
                local_flat[nm] = flat
                substates_of[nm] = [flat]
            all_names.setdefault(nm, local_flat.get(nm)
                                 or entry_of.get(nm) or flat)

        for ps in level.get("pseudostates", []) or []:
            nm = ps.get("name") if isinstance(ps, dict) else ps
            if not nm:
                continue
            flat = prefix + nm
            region_flat = prefix[:-1] if prefix else ""
            if nm in local_flat or nm in entry_of:
                notes.append(
                    f"pseudostate {flat!r} shadows a state of the same "
                    "name; treating it as a state")
                continue
            markers_flat[flat] = region_flat
            all_names.setdefault(nm, flat)

        for t in level.get("transitions", []):
            src, tgt = t.get("source"), t.get("target")
            if src in substates_of and src not in local_flat:
                # composite as source: one transition per substate
                q_tgt = (local_flat.get(tgt) or entry_of.get(tgt)
                         or tgt)
                for sub in substates_of[src]:
                    raw.append({
                        "name": ((t.get("name") or "t") +
                                 f"@{sub}"),
                        "source": sub, "target": q_tgt,
                        "trigger": t.get("trigger"),
                        "guard": t.get("guard"),
                        "effect": t.get("effect"),
                    })
                continue
            raw.append({
                "name": t.get("name"),
                "source": (local_flat.get(src) or entry_of.get(src)
                           or src),
                "target": (local_flat.get(tgt) or entry_of.get(tgt)
                           or tgt),
                "trigger": t.get("trigger"),
                "guard": t.get("guard"),
                "effect": t.get("effect"),
            })
        return local_flat, entry_of, substates_of

    all_names: Dict[str, str] = {}
    _, entry_of, _ = _expand_region(sm, "", all_names)

    # v0.89.0: the machine root itself may be a parallel region set
    # (``state def M parallel { ... }``) — every top-level state is a
    # co-active region.  The tracked leaf per region is its default
    # entry (its own flat name for leaf regions, the initial substate
    # for composite regions).
    if sm.get("parallel") and len(states) > 1:
        region_leaves = []
        region_names = []
        for s in sm.get("states", []):
            nm = _state_name(s)
            if nm is None:
                continue
            if _has_region(s):
                cl = region_defaults_flat.get(nm)
                if nm in entry_of:
                    cl = cl or entry_of.get(nm)
                if cl:
                    region_leaves.append(cl)
                    region_names.append(nm)
            elif nm in all_names:
                cl = all_names.get(nm)
                if cl in states:
                    region_leaves.append(cl)
                    region_names.append(nm)
        if len(region_leaves) > 1:
            parallel_regions[""] = tuple(region_names)
            notes.append(
                f"machine {sm.get('name')!r} declares parallel regions; "
                f"{len(region_leaves)} co-active top-level regions")

    transitions: List[TransitionSpec] = []
    skipped: List[TransitionSpec] = []
    for t in raw:
        source, target = t.get("source"), t.get("target")
        if source is None or target is None:
            notes.append(
                f"transition {t.get('name')!r} skipped: unresolved "
                f"endpoint(s) (source={source!r}, target={target!r})")
            skipped.append(TransitionSpec(
                name=t.get("name"), source=source, target=target,
                trigger=t.get("trigger"), guard=t.get("guard"),
                effect=t.get("effect")))
            continue
        # bare-name references to states declared anywhere in the
        # machine (e.g. a machine-level transition naming a composite's
        # substate) resolve to the qualified flat name
        source = all_names.get(source, source)
        target = all_names.get(target, target)
        if target in markers_flat:
            # history target: the transition re-enters the region's
            # last active substate at fire time; the static dest is
            # the region's default entry (used before any history)
            region_flat = markers_flat[target]
            dest = region_defaults_flat.get(region_flat)
            if dest is None or dest not in states:
                notes.append(
                    f"transition {t.get('name')!r} skipped: history "
                    f"region {region_flat or '(machine)'!r} has no "
                    "default entry to fall back to")
                skipped.append(TransitionSpec(
                    name=t.get("name"), source=source, target=target,
                    trigger=t.get("trigger"), guard=t.get("guard"),
                    effect=t.get("effect"),
                    history_region=region_flat))
                continue
            transitions.append(TransitionSpec(
                name=t.get("name"), source=source, target=dest,
                trigger=t.get("trigger"), guard=t.get("guard"),
                effect=t.get("effect"), history_region=region_flat))
            continue
        if source not in states or target not in states:
            notes.append(
                f"transition {t.get('name')!r} skipped: endpoint(s) "
                f"name no state in the machine "
                f"(source={source!r}, target={target!r})")
            skipped.append(TransitionSpec(
                name=t.get("name"), source=source, target=target,
                trigger=t.get("trigger"), guard=t.get("guard"),
                effect=t.get("effect")))
            continue
        # v0.89.0: parallel-region entry/exit markers, resolved against
        # the region flat names — a transition stays inside its region
        # when both endpoints belong to the same region; leaving the
        # region's subtree exits every co-active region of the
        # composite, and a target inside a parallel composite activates
        # all of its regions.
        def _region_in(comp, name):
            return next((r for r in parallel_regions[comp]
                         if name == r or name.startswith(r + ".")), None)

        exits_comp = None
        enters_comp = None
        for comp, region_names in parallel_regions.items():
            src_region = _region_in(comp, source)
            tgt_region = _region_in(comp, target)
            if src_region is not None and src_region != tgt_region:
                # leave src_region; keep the OUTERMOST composite whose
                # region set diverges (exiting only the inner one would
                # strand the outer)
                if exits_comp is None or \
                        exits_comp.startswith(comp + "."):
                    exits_comp = comp
                if tgt_region is not None:
                    enters_comp = comp
            elif src_region is None and tgt_region is not None:
                if enters_comp is None or \
                        comp.startswith(enters_comp + "."):
                    enters_comp = comp
        transitions.append(TransitionSpec(
            name=t.get("name"), source=source, target=target,
            trigger=t.get("trigger"), guard=t.get("guard"),
            effect=t.get("effect"),
            enters_parallel=enters_comp, exits_parallel=exits_comp))

    if not states:
        raise SimulationError(
            f"State machine {sm.get('name')!r} has no states to "
            "simulate.")

    initial = sm.get("initial")
    if initial in entry_of:
        notes.append(
            f"entering composite {initial!r} at its initial substate "
            f"{entry_of[initial]!r}")
        initial = entry_of[initial]
    if initial is None or initial not in states:
        fallback = states[0]
        notes.append(
            f"no entry transition in the model; starting in "
            f"{fallback!r} (the first declared state)")
        initial = fallback
    # v0.89.0: a parallel machine root formally starts in the first
    # region's leaf; the other regions activate at construction time.
    if "" in parallel_regions:
        initial = parallel_regions[""][0]
    region_defaults_flat[""] = initial
    # v0.89.0: containment of parallel composites — the enclosing
    # parallel composite is the longest other composite whose flat name
    # prefixes this one (region paths are unique).
    parallel_parent_flat: Dict[str, str] = {}
    for comp in parallel_regions:
        best = ""
        for other in parallel_regions:
            if other != comp and other != "" and \
                    comp.startswith(other + "."):
                if other.startswith(best + ".") or not best:
                    best = other
        parallel_parent_flat[comp] = best
    return MachineDescriptor(name=sm.get("name"), states=states,
                             initial=initial, transitions=transitions,
                             notes=notes, skipped=tuple(skipped),
                             history_markers=markers_flat,
                             region_defaults=region_defaults_flat,
                             parallel_regions=parallel_regions,
                             parallel_parent=parallel_parent_flat)


def load_model_grammar(model) -> dict:
    """Raw, faithful parser dictionary for *model* (evaluator pattern)."""
    try:
        text = model.dump()
    except Exception:
        text = ""
    if not text or not text.strip():
        raise SimulationError(
            "The model does not round-trip to SysML text for "
            "simulation.")
    import sysmlpy

    try:
        return sysmlpy.load_grammar(text)
    except SysMLSyntaxError as e:
        raise SimulationError(f"The model does not re-parse: {e}") from e


# ---------------------------------------------------------------------------
# The simulator
# ---------------------------------------------------------------------------

class StepRecord:
    """One entry in the simulation log (an attempt to fire)."""

    def __init__(self, from_state: str, trigger: Optional[str],
                 guard: Optional[str], guard_ok: Optional[bool],
                 to_state: Optional[str], effects: List[str],
                 fired: bool, note: str = "",
                 assignments: Tuple[Tuple[str, Any], ...] = ()):
        self.from_state = from_state
        self.trigger = trigger
        self.guard = guard
        self.guard_ok = guard_ok
        self.to_state = to_state
        self.effects = effects
        self.fired = fired
        self.note = note
        #: (name, value) pairs applied by ``do x := <expr>`` effects.
        self.assignments = tuple(assignments)
        self.timestamp = time.time()

    def __repr__(self):
        arrow = "->" if self.fired else "-x"
        trig = self.trigger or "(completion)"
        out = (f"<{arrow} {self.from_state!r} --{trig}"
               f"[{self.guard}]--> {self.to_state!r}>")
        if self.assignments:
            assign = ", ".join(f"{n} := {v!r}" for n, v in self.assignments)
            out += f" {assign}"
        return out


def _make_host(sim: "StateSimulator", n_guards: int, n_effects: int):
    """Build the pytransitions model object with guard/effect methods.

    pytransitions resolves conditions and callbacks by method *name*
    on the model and invokes them as ``func(event_data)``; methods are
    generated here so each closes over its own transition index.
    """

    class Host:
        pass

    for i in range(n_guards):
        def _guard(self, event=None, _i=i):
            return sim._eval_guard(_i)
        setattr(Host, f"_guard_{i}", _guard)
    for i in range(n_effects):
        def _effect(self, event=None, _i=i):
            sim._do_effect(_i)
        setattr(Host, f"_effect_{i}", _effect)
    return Host()


class StateSimulator:
    """Simulate one state machine of a parsed SysML v2 model.

    Parameters
    ----------
    model : Model
        Parsed model (as taken by the view functions).
    focus : str, optional
        Name of the ``state def``/``state`` machine to simulate;
        defaults to the first machine found.
    values : dict, optional
        Starting attribute values for guard evaluation; defaults to
        the model's evaluated attribute values
        (:func:`sysmlpy.evaluator.collect_values`).  Keys may be bare
        names or qualified names.
    """

    def __init__(self, model, focus: Optional[str] = None,
                 values: Optional[Dict[str, Any]] = None,
                 deep_history: bool = False):
        self.model = model
        self.descriptor = build_state_machine(model, focus=focus)
        self.notes = list(self.descriptor.notes)
        #: When True, history pseudostates restore the deepest visited
        #: state; by default (False) they restore one level (shallow).
        self.deep_history = bool(deep_history)
        #: name -> value; guards evaluate against these (overrides on
        #: top of the model's collected attribute values).
        self.values: Dict[str, Any] = dict(values or {})
        if values is None:
            try:
                self.values.update(collect_values(model))
            except EvaluationError:
                pass
        self.log: List[StepRecord] = []
        self._pending_effects: List[str] = []
        self._pending_assignments: List[Tuple[str, Any]] = []
        #: region flat name -> last active direct substate of that
        #: region ("" = machine root)
        self._history: Dict[str, str] = {}
        #: parallel-region flat name -> its currently active leaf
        #: (v0.89.0).  A parallel composite is entered while all of
        #: its regions appear here; nested composites expand into
        #: their own region entries.
        self._region_state: Dict[str, str] = {}
        self._host = _make_host(
            self, len(self.descriptor.transitions),
            len(self.descriptor.transitions))
        self._build()
        self._activate_initial()
        self._record_all_history()

    # -- history ------------------------------------------------------------

    def _record_all_history(self):
        for leaf in self._all_active_leaves():
            self._record_history(leaf)

    def _all_active_leaves(self) -> List[str]:
        """Every currently active leaf, in declaration order.

        Walks the entered parallel composites outermost-first; a
        region whose tracked leaf heads a nested entered composite
        expands into that composite's regions (v0.89.0).  For
        orthogonal machines this is the single pytransitions state.
        """
        out: List[str] = []

        def walk(comp: str):
            for r in self.descriptor.parallel_regions.get(comp, ()):
                leaf = self._region_state.get(r)
                if leaf is None:
                    continue
                # the leaf may head a nested parallel composite
                nested = next((c for c in self.descriptor.parallel_regions
                               if c != comp and c != "" and
                               c.startswith(r + ".")), None)
                if nested is not None and all(
                        nr in self._region_state
                        for nr in self.descriptor.parallel_regions[nested]):
                    walk(nested)
                else:
                    out.append(leaf)

        entered = [c for c in self.descriptor.parallel_regions
                   if all(r in self._region_state
                          for r in self.descriptor.parallel_regions[c])]
        if not entered:
            return [self._host.state]
        # outermost entered composites (parent not entered), plus the
        # orthogonal host state when nothing covers it
        covered = False
        for comp in entered:
            parent = self.descriptor.parallel_parent.get(comp, "")
            if parent and parent in entered:
                continue
            walk(comp)
            if any(self._region_state.get(r) == self._host.state
                   for r in self.descriptor.parallel_regions[comp]):
                covered = True
        if not covered and self._host.state not in out:
            out.insert(0, self._host.state)
        return [s for s in out if s]

    def _record_history(self, state: str):
        """Remember the active direct substate of every enclosing region.

        For state ``C.Inner.Deep.S`` this records ``"" -> C``,
        ``C -> C.Inner``, ``C.Inner -> C.Inner.Deep`` and
        ``C.Inner.Deep -> C.Inner.Deep.S`` — i.e. each region maps to
        its direct active child, which is what shallow history resumes;
        deep history follows the chain down.
        """
        if not state:
            return
        parts = state.split(".")
        for i in range(len(parts)):
            self._history[".".join(parts[:i])] = ".".join(parts[:i + 1])

    def _resolve_history(self, region_flat: str) -> Optional[str]:
        """State to resume when re-entering *region_flat* via history."""
        rd = self.descriptor.region_defaults
        default = rd.get(region_flat) or self.descriptor.initial
        s = self._history.get(region_flat)
        if s is None:
            return default
        if not self.deep_history:
            # shallow: the recorded direct child; if it is a composite,
            # enter at its initial substate
            if s in self.descriptor.states:
                return s
            return rd.get(s) or default
        seen = set()
        while (s is not None and s not in self.descriptor.states
               and s not in seen):
            seen.add(s)
            s = self._history.get(s) or rd.get(s)
        return s or default

    def _apply_history(self, t: TransitionSpec) -> str:
        """Post-fire state adjustment for history-targeting transitions.

        pytransitions needs a concrete ``dest`` per transition, so
        history transitions are defined to the region's default entry
        and the actual (recorded) state is applied right after firing.
        """
        if t.history_region is None:
            return t.target
        resolved = self._resolve_history(t.history_region)
        if resolved and resolved != self.state:
            self._host.state = resolved
        return resolved or t.target

    # -- construction -------------------------------------------------------

    def _build(self):
        """(Re)build the pytransitions machine in its initial state."""
        md = self.descriptor
        tdefs = []
        for i, t in enumerate(md.transitions):
            # one pytransitions event per TRANSITION (not per trigger
            # name) so guarded alternatives fall through in my order
            tdefs.append({
                "trigger": f"fire_{i}",
                "source": t.source,
                "dest": t.target,
                "conditions": [f"_guard_{i}"] if t.guard else [],
                "after": [f"_effect_{i}"] if t.effect else [],
            })
        self._machine = Machine(
            model=self._host, states=md.states, initial=md.initial,
            transitions=tdefs, auto_transitions=False)

    @property
    def state(self):
        """Current state name.

        A plain string for orthogonal machines; a tuple of leaves in
        declaration order while co-active parallel regions are live
        (v0.89.0).
        """
        leaves = self._all_active_leaves()
        if len(leaves) == 1:
            return leaves[0]
        return tuple(leaves)

    # -- parallel regions (v0.89.0) -------------------------------------------

    def _entered_set(self) -> set:
        """Parallel composites currently entered (all regions have a
        tracked leaf)."""
        return {c for c in self.descriptor.parallel_regions
                if all(r in self._region_state
                       for r in self.descriptor.parallel_regions[c])}

    def _default_leaves(self, comp: str) -> Tuple[str, ...]:
        """Default-entry leaf of each region of parallel composite
        *comp*, in declaration order."""
        return tuple(
            self.descriptor.region_defaults.get(r, r)
            for r in self.descriptor.parallel_regions.get(comp, ()))

    def _activate_initial(self):
        """Activate the initial region set of the root — or, when the
        initial leaf lies inside a parallel composite, that composite's
        region set (v0.89.0)."""
        root_regions = self.descriptor.parallel_regions.get("")
        if root_regions:
            self._activate_regions("", self._default_leaves(""))
            return
        for comp in self.descriptor.parallel_regions:
            if self.descriptor.initial in self._default_leaves(comp):
                self._activate_regions(
                    comp, self._default_leaves(comp))
                return

    def _activate_regions(self, comp: str, leaves: Tuple[str, ...],
                          entered_leaf: Optional[str] = None):
        """Enter parallel composite *comp* with every region active.

        *leaves* holds the entry leaf per region (declaration order);
        a region containing a nested parallel composite activates that
        composite's subregions recursively.  *entered_leaf* is the
        leaf the fired transition entered at — its region becomes the
        tracked (pytransitions) primary (v0.89.0)."""
        regions = self.descriptor.parallel_regions.get(comp, ())
        primary_region = None
        for i, r in enumerate(regions):
            leaf = leaves[i] if i < len(leaves) else r
            self._region_state[r] = leaf
            # a nested parallel composite under this region activates
            # with it; the region's tracked leaf becomes the nested
            # primary
            nested = next((c for c in self.descriptor.parallel_regions
                           if c != "" and c.startswith(r + ".")), None)
            if nested is not None:
                self._activate_regions(nested, self._default_leaves(nested),
                                       entered_leaf=leaf)
                self._region_state[r] = self._region_state.get(
                    self.descriptor.parallel_regions[nested][0], leaf)
            if entered_leaf is not None and \
                    self._region_state.get(r) == entered_leaf and \
                    primary_region is None:
                primary_region = r
        if primary_region is None:
            primary_region = next((r for r in regions
                                   if r in self._region_state), None)
            if primary_region is None and regions:
                primary_region = regions[0]
                if primary_region not in self._region_state:
                    self._region_state[primary_region] = (
                        leaves[0] if leaves else primary_region)
        if primary_region is not None:
            self._host.state = self._region_state.get(
                primary_region, self._host.state)
        for leaf in list(self._region_state.values()):
            self._record_history(leaf)

    def _deactivate_regions(self, comp: Optional[str]):
        """Leave parallel composite *comp* — nested composites inside
        its subtree go with it (v0.89.0).  ``comp`` may be None when
        the fired transition carried no parallel marker."""
        if comp is None:
            return
        doomed_regions: List[str] = []
        for other in self.descriptor.parallel_regions:
            if other == comp:
                doomed_regions.extend(self.descriptor.parallel_regions[other])
            else:
                parent = other
                while parent:
                    parent = self.descriptor.parallel_parent.get(parent, "")
                    if parent == comp:
                        doomed_regions.extend(
                            self.descriptor.parallel_regions[other])
                        break
        for r in doomed_regions:
            self._region_state.pop(r, None)

    def _composites_active(self):
        """Parallel composite flat names currently entered."""
        return self._entered_set()

    def _region_of_leaf(self, leaf: str) -> Optional[str]:
        """Region flat whose tracked leaf is *leaf* (deepest match)."""
        best = None
        for comp in self.descriptor.parallel_regions:
            for r in self.descriptor.parallel_regions[comp]:
                if self._region_state.get(r) == leaf:
                    if best is None or len(r) > len(best):
                        best = r
        return best

    def _candidates(self, state: str, trigger: Optional[str] = None):
        """Transition indices from *state* (optionally for *trigger*)."""
        return [
            i for i, t in enumerate(self.descriptor.transitions)
            if t.source == state
            and (trigger is None or
                 (t.trigger and _mangle(t.trigger) == _mangle(trigger)))]

    def send(self, trigger: str) -> bool:
        """Fire *trigger* from the current state; returns whether it fired.

        When several transitions carry the same trigger, the first one
        whose guard holds fires (guard fall-through, Cameo-style).
        With co-active parallel regions (v0.89.0) the trigger is
        dispatched to each region in declaration order.
        """
        for current in self._all_active_leaves():
            indices = [i for i, t in enumerate(self.descriptor.transitions)
                       if t.source == current and t.trigger
                       and _mangle(t.trigger) == _mangle(trigger)]
            if not indices:
                continue
            for i in indices:
                if self._eval_guard(i):
                    return self._fire(i)
            t = self.descriptor.transitions[indices[0]]
            self.log.append(StepRecord(
                current, trigger, t.guard, False, None, [], False,
                note="guard false"))
            return False
        self.log.append(StepRecord(
            self.state, trigger, None, None, None, [], False,
            note=(f"'{trigger}' is not a trigger from "
                  f"{self.state!r}")))
        return False

    def step(self) -> bool:
        """Fire the first enabled transition from the current state.

        Completion transitions (no trigger) are preferred; otherwise
        the first signal transition whose guard holds fires.  With
        co-active parallel regions (v0.89.0) each region is offered
        the step in declaration order.
        """
        for current in self._all_active_leaves():
            indices = [i for i, t in enumerate(self.descriptor.transitions)
                       if t.source == current]
            for i in indices:  # completion transitions first (UML RTC)
                if self.descriptor.transitions[i].trigger is None:
                    if self._eval_guard(i):
                        return self._fire(i)
            for i in indices:
                t = self.descriptor.transitions[i]
                if t.trigger and self._eval_guard(i):
                    return self._fire(i)
        self.log.append(StepRecord(
            self.state, None, None, None, None, [], False,
            note="no enabled transition"))
        return False

    def reset(self):
        """Return to the initial state and clear the log."""
        self.log.clear()
        # A fresh host too: pytransitions refuses to re-bind event
        # methods it already put on the previous host (model override
        # policy), so rebuilding on the same object would keep stale
        # transitions wired.
        self._host = _make_host(
            self, len(self.descriptor.transitions),
            len(self.descriptor.transitions))
        self._build()
        self._region_state.clear()
        self._activate_initial()
        self._history.clear()
        self._record_all_history()

    def _fire(self, index: int) -> bool:
        t = self.descriptor.transitions[index]
        self._pending_effects.clear()
        self._pending_assignments.clear()
        old_primary = self._host.state
        co_region = self._region_of_leaf(t.source)
        manual = co_region is not None and t.source != self._host.state
        if manual:
            # v0.89.0: the source lies in a co-active parallel region
            # that pytransitions does not track — fire manually.
            if not self._eval_guard(index):
                self.log.append(StepRecord(
                    t.source, t.trigger, t.guard, False, None, [], False,
                    note="guard false"))
                return False
            self._do_effect(index)
            fired = True
        else:
            fired = bool(getattr(self._host, f"fire_{index}")())
        if fired:
            # v0.89.0: parallel-region bookkeeping.
            if t.enters_parallel is not None and \
                    t.exits_parallel == t.enters_parallel:
                # cross-region move inside one composite: the source
                # region leaves, the target region enters at the target
                src_region = self._region_containing(
                    t.exits_parallel, t.source)
                if src_region is not None:
                    self._region_state.pop(src_region, None)
                tgt_region = self._region_containing(
                    t.enters_parallel, t.target)
                if tgt_region is not None:
                    self._region_state[tgt_region] = t.target
                for r, leaf in list(self._region_state.items()):
                    if leaf == t.source:
                        self._region_state[r] = t.target
                if old_primary == t.source:
                    self._host.state = t.target
            elif t.enters_parallel is not None:
                self._enter_at(t.enters_parallel, t.target)
            elif t.exits_parallel is not None:
                self._deactivate_regions(t.exits_parallel)
                for r, leaf in list(self._region_state.items()):
                    if leaf == old_primary:
                        self._region_state[r] = self._host.state
            else:
                # region-internal fire: the fired region's leaf moves
                # to the target, and every slot mirroring it follows
                # (a nested composite's primary is also its parent's
                # slot)
                if co_region is not None:
                    self._region_state[co_region] = t.target
                for r, leaf in list(self._region_state.items()):
                    if leaf == t.source:
                        self._region_state[r] = t.target
                self._retrack_parents()
            to_state = self._apply_history(t)
            self._record_all_history()
            note = ""
            if t.enters_parallel is not None:
                note = (f"parallel: entered "
                        f"{t.enters_parallel or '(machine root)'!r} "
                        f"with regions "
                        f"{tuple(self._region_state.get(r) for r in self.descriptor.parallel_regions.get(t.enters_parallel, ()))!r}")
            elif t.exits_parallel is not None:
                note = (f"parallel: exited "
                        f"{t.exits_parallel or '(machine root)'!r}")
            if t.history_region is not None and to_state != t.target:
                note = (f"history: resumed {to_state!r} in region "
                        f"{t.history_region or '(machine)'!r}")
            self.log.append(StepRecord(
                t.source, t.trigger, t.guard, True, to_state,
                list(self._pending_effects), True, note,
                assignments=tuple(self._pending_assignments)))
            self._pending_effects.clear()
            self._pending_assignments.clear()
            self._run_completion()
            return True
        self.log.append(StepRecord(
            t.source, t.trigger, t.guard, False, None, [], False,
            note="transition not taken"))
        return False

    def _enter_at(self, comp: str, target: str):
        """Enter parallel composite *comp*, pinning the region that
        contains *target* to *target* and making it the tracked
        primary (v0.89.0)."""
        leaves = list(self._default_leaves(comp))
        entered_leaf = None
        for i, r in enumerate(
                self.descriptor.parallel_regions.get(comp, ())):
            if target == r or target.startswith(r + "."):
                leaves[i] = target
                entered_leaf = target
                break
        self._activate_regions(comp, tuple(leaves),
                               entered_leaf=entered_leaf)

    def _region_containing(self, comp: str, name: str) -> Optional[str]:
        """Region of parallel composite *comp* whose subtree contains
        *name* (v0.89.0)."""
        for r in self.descriptor.parallel_regions.get(comp, ()):
            if name == r or name.startswith(r + "."):
                return r
        return None

    def _retrack_parents(self):
        """Point every parent-composite slot that heads a nested
        entered composite at that composite's primary leaf (v0.89.0)."""
        for comp, regions in self.descriptor.parallel_regions.items():
            if comp == "":
                continue
            for r in regions:
                nested = next(
                    (c for c in self.descriptor.parallel_regions
                     if c != "" and c.startswith(r + ".")), None)
                if nested is None:
                    continue
                nregions = self.descriptor.parallel_regions[nested]
                if all(nr in self._region_state for nr in nregions):
                    self._region_state[r] = self._region_state.get(
                        nregions[0], self._region_state.get(r))

    def _run_completion(self, limit: int = 100):
        """Fire enabled completion transitions until none remain.

        With co-active parallel regions (v0.89.0) every region is
        offered its completion transitions each round.
        """
        for _ in range(limit):
            fired_any = False
            for current in self._all_active_leaves():
                for i, t in enumerate(self.descriptor.transitions):
                    if t.source == current and t.trigger is None:
                        if self._eval_guard(i):
                            if self._fire(i):
                                fired_any = True
                            break
                if fired_any:
                    break
            if not fired_any:
                return

    # -- inspection -------------------------------------------------------------

    def available(self) -> List[Tuple[Optional[str], Optional[str],
                                      Optional[bool]]]:
        """Transitions from the current state(s), in declaration order.

        Returns ``(trigger, guard_text, passes_now)``; completion
        transitions report the trigger as ``None``, guard-less ones
        ``passes_now = None``.  With co-active parallel regions
        (v0.89.0) every region's transitions are listed, annotated
        with the region leaf as a fourth element.
        """
        out = []
        for t in self.descriptor.transitions:
            if t.source not in self._all_active_leaves():
                continue
            ok = self._eval_guard_quiet(t.guard) if t.guard else None
            out.append((t.trigger, t.guard, ok))
        return out

    def set_value(self, name: str, value: Any):
        """Override an attribute value used by guard evaluation."""
        self.values[name] = value

    # -- guard/effect evaluation -------------------------------------------------

    def _eval_guard(self, index: int) -> bool:
        guard = self.descriptor.transitions[index].guard
        if not guard:
            return True
        try:
            return bool(evaluate_expression(
                guard, model=self.model, bindings=self.values))
        except EvaluationError:
            return False

    def _eval_guard_quiet(self, guard: Optional[str]) -> Optional[bool]:
        if not guard:
            return None
        try:
            return bool(evaluate_expression(
                guard, model=self.model, bindings=self.values))
        except EvaluationError:
            return None

    def _do_effect(self, index: int):
        effect = self.descriptor.transitions[index].effect
        if not effect:
            return
        m = _ASSIGNMENT_RE.match(effect)
        if m:
            # Assignment effect (``do x := <expr>``): evaluate and
            # apply through set_value so later guards see the result.
            name, expr = m.group(1), m.group(2)
            try:
                value = evaluate_expression(
                    expr, model=self.model, bindings=self.values)
            except EvaluationError as e:
                self._pending_effects.append(
                    f"{effect} (not evaluated: {e})")
                return
            self.set_value(name, value)
            self._pending_assignments.append((name, value))
            self._pending_effects.append(effect)
            return
        self._pending_effects.append(effect)


# ---------------------------------------------------------------------------
# Interactive TUI
# ---------------------------------------------------------------------------

def _render(sim: StateSimulator) -> str:
    md = sim.descriptor
    state = sim.state
    active = (state if isinstance(state, tuple) else (state,))
    lines = [f"State machine {md.name or '(unnamed)'} — "
             f"current: {state!r}"]
    for s in md.states:
        marker = "  >" if s in active else "    "
        lines.append(f"{marker} {s}")
    lines.append("transitions from here:")
    avail = sim.available()
    if not avail:
        lines.append("    (none)")
    for n, (trigger, guard, ok) in enumerate(avail):
        trig = trigger or "(completion)"
        guard_txt = f" when {guard}" if guard else ""
        status = ""
        if ok is not None:
            status = "  [guard: TRUE]" if ok else "  [guard: false]"
        lines.append(f"  {n}) {trig or '(completion)'}{guard_txt}"
                     f" -> (target){status}")
    return "\n".join(lines)


def run_tui(model, focus: Optional[str] = None,
            values: Optional[Dict[str, Any]] = None,
            deep_history: bool = False,
            input_func=input, output=print) -> Optional[StateSimulator]:
    """Interactive simulate-test loop; returns the simulator on exit.

    Uses *input_func*/*output* (defaulting to ``input``/``print``) so
    tests can drive it headlessly.  On a non-interactive stream it
    prints one snapshot and returns instead of looping.
    """
    try:
        sim = StateSimulator(model, focus=focus, values=values,
                             deep_history=deep_history)
    except SimulationError as e:
        output(f"simulation: {e}")
        return None
    output(_render(sim))
    for note in sim.notes:
        output(f"note: {note}")
    output("commands: <n> fire · <Trigger> fire · step · set name=value "
           "· values · log · q")
    while True:
        try:
            line = input_func("> ")
        except (EOFError, StopIteration):
            break
        if line is None:
            break
        line = line.strip()
        if not line:
            continue
        if line in ("q", "quit", "exit"):
            break
        if line == "step":
            fired = sim.step()
            output("fired" if fired else "no enabled transition")
        elif line == "values":
            for k in sorted(sim.values):
                output(f"  {k} = {sim.values[k]!r}")
        elif line == "log":
            for rec in sim.log:
                output(repr(rec))
        elif line.startswith("set "):
            try:
                name, _, raw = line[4:].partition("=")
                sim.set_value(name.strip(), _parse_value(raw.strip()))
                output(f"{name.strip()} = {sim.values[name.strip()]!r}")
            except (ValueError, SyntaxError) as e:
                output(f"could not set value: {e}")
        elif line.isdigit():
            avail = sim.available()
            i = int(line)
            if 0 <= i < len(avail):
                trigger = avail[i][0] or ""
                fired = sim.send(trigger) if trigger else sim.step()
                output("fired" if fired else "blocked (guard false)")
            else:
                output(f"no transition {i}")
        else:
            fired = sim.send(line)
            output("fired" if fired else f"blocked: '{line}'")
        output("")
        output(_render(sim))
    return sim


def _parse_value(raw: str):
    """Literal value for ``--set``/``set`` (bool/int/float/str)."""
    text = raw.strip()
    if text.lower() in ("true", "false"):
        return text.lower() == "true"
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        return text