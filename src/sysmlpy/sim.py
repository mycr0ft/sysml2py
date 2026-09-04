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
  — top-level or inside a composite — raise :class:`SimulationError`
- effects are logged, not executed; assignment effects surface as
  ``target := value`` text — executing them would flow through
  :meth:`StateSimulator.set_value` and is a follow-up
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

    if sm.get("parallel"):
        raise SimulationError(
            f"State machine {sm.get('name')!r} declares parallel "
            "regions; parallel simulation is beyond this MVP.")

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
    #   - a region declaring parallel raises (MVP cut).
    states: List[str] = []
    raw: List[dict] = []

    def _expand_region(level, prefix, all_names):
        local_flat: Dict[str, str] = {}
        entry_of: Dict[str, str] = {}
        substates_of: Dict[str, List[str]] = {}

        for s in level.get("states", []):
            nm = _state_name(s)
            if nm is None:
                continue
            if isinstance(s, dict) and s.get("parallel"):
                raise SimulationError(
                    f"Composite state {nm!r} in "
                    f"{sm.get('name')!r} declares parallel regions; "
                    "parallel simulation is beyond this MVP.")
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
                    # region without simulating states: a leaf
                    flat = prefix + nm
                    states.append(flat)
                    local_flat[nm] = flat
                    substates_of[nm] = [flat]
                    continue
                entry_of[nm] = entry
                substates_of[nm] = (list(inner_flat.values()) +
                                    list(inner_entry.values()))
            else:
                flat = prefix + nm
                states.append(flat)
                local_flat[nm] = flat
                substates_of[nm] = [flat]
            all_names.setdefault(nm, local_flat.get(nm)
                                 or entry_of.get(nm) or flat)

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
        transitions.append(TransitionSpec(
            name=t.get("name"), source=source, target=target,
            trigger=t.get("trigger"), guard=t.get("guard"),
            effect=t.get("effect")))

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
    return MachineDescriptor(name=sm.get("name"), states=states,
                             initial=initial, transitions=transitions,
                             notes=notes, skipped=tuple(skipped))


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
                 fired: bool, note: str = ""):
        self.from_state = from_state
        self.trigger = trigger
        self.guard = guard
        self.guard_ok = guard_ok
        self.to_state = to_state
        self.effects = effects
        self.fired = fired
        self.note = note
        self.timestamp = time.time()

    def __repr__(self):
        arrow = "->" if self.fired else "-x"
        trig = self.trigger or "(completion)"
        return (f"<{arrow} {self.from_state!r} --{trig}"
                f"[{self.guard}]--> {self.to_state!r}>")


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
                 values: Optional[Dict[str, Any]] = None):
        self.model = model
        self.descriptor = build_state_machine(model, focus=focus)
        self.notes = list(self.descriptor.notes)
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
        self._host = _make_host(
            self, len(self.descriptor.transitions),
            len(self.descriptor.transitions))
        self._build()

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
    def state(self) -> str:
        """Current state name."""
        return self._host.state

    # -- driving --------------------------------------------------------------

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
        """
        current = self.state
        indices = [i for i, t in enumerate(self.descriptor.transitions)
                   if t.source == current and t.trigger
                   and _mangle(t.trigger) == _mangle(trigger)]
        if not indices:
            self.log.append(StepRecord(
                current, trigger, None, None, None, [], False,
                note=f"'{trigger}' is not a trigger from {current!r}"))
            return False
        for i in indices:
            if self._eval_guard(i):
                return self._fire(i)
        t = self.descriptor.transitions[indices[0]]
        self.log.append(StepRecord(
            current, trigger, t.guard, False, None, [], False,
            note="guard false"))
        return False

    def step(self) -> bool:
        """Fire the first enabled transition from the current state.

        Completion transitions (no trigger) are preferred; otherwise
        the first signal transition whose guard holds fires.
        """
        current = self.state
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
            current, None, None, None, None, [], False,
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

    def _fire(self, index: int) -> bool:
        t = self.descriptor.transitions[index]
        self._pending_effects.clear()
        fired = bool(getattr(self._host, f"fire_{index}")())
        if fired:
            self.log.append(StepRecord(
                t.source, t.trigger, t.guard, True, t.target,
                list(self._pending_effects), True))
            self._pending_effects.clear()
            self._run_completion()
            return True
        self.log.append(StepRecord(
            t.source, t.trigger, t.guard, False, None, [], False,
            note="transition not taken"))
        return False

    def _run_completion(self, limit: int = 100):
        """Fire enabled completion transitions until none remain."""
        for _ in range(limit):
            current = self.state
            fired_any = False
            for i, t in enumerate(self.descriptor.transitions):
                if t.source == current and t.trigger is None:
                    if self._eval_guard(i):
                        self._pending_effects.clear()
                        getattr(self._host, f"fire_{i}")()
                        self.log.append(StepRecord(
                            t.source, None, t.guard, True, t.target,
                            list(self._pending_effects), True))
                        self._pending_effects.clear()
                        fired_any = True
                        break
            if not fired_any:
                return

    # -- inspection -------------------------------------------------------------

    def available(self) -> List[Tuple[Optional[str], Optional[str],
                                      Optional[bool]]]:
        """Transitions from the current state, in declaration order.

        Returns ``(trigger, guard_text, passes_now)``; completion
        transitions report the trigger as ``None``, guard-less ones
        ``passes_now = None``.
        """
        out = []
        for t in self.descriptor.transitions:
            if t.source != self.state:
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
        if effect:
            self._pending_effects.append(effect)


# ---------------------------------------------------------------------------
# Interactive TUI
# ---------------------------------------------------------------------------

def _render(sim: StateSimulator) -> str:
    md = sim.descriptor
    lines = [f"State machine {md.name or '(unnamed)'} — "
             f"current: {sim.state!r}"]
    for s in md.states:
        marker = "  >" if s == sim.state else "    "
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
            input_func=input, output=print) -> Optional[StateSimulator]:
    """Interactive simulate-test loop; returns the simulator on exit.

    Uses *input_func*/*output* (defaulting to ``input``/``print``) so
    tests can drive it headlessly.  On a non-interactive stream it
    prints one snapshot and returns instead of looping.
    """
    try:
        sim = StateSimulator(model, focus=focus, values=values)
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