#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Adapter that renders a sysmlpy state machine as a `boxes` Diagram.

Walks the visitor dict produced by :func:`sysmlpy.load_grammar` to find
StateDefinition / StateUsage / TransitionUsage / EntryTransitionMember nodes
and emits a boxes Diagram with:

- rounded ``Node`` (stereotype ``«state»``) for each ``state`` member
- a filled ``StartNode`` (initial pseudostate) for each ``entry; then X;``
- an ``Edge`` from the initial pseudostate to the target state (no arrowhead)
- an ``Edge`` between states for each ``transition X first A accept B then C``
  with the trigger name as the label

The boxes pseudostate shapes already match UML/SysML notation:
``StartNode`` = filled circle (initial), ``DoneNode`` = bullseye (final),
``DecisionNode`` = diamond (choice), ``ForkJoinNode`` = thick bar (fork/join),
``TerminateNode`` = X-in-circle (terminate). These are imported and re-aliased
as the state-machine pseudostates to make intent explicit in client code.

Public API
----------
``as_state_transition_view_boxes(model, focus=None) -> boxes.Diagram``
    Build a Diagram from a parsed model (or a SysML text string).
``render_state_transition_view(model, focus=None, routing='orthogonal') -> str``
    Convenience: build + render to terminal braille string.
``render_state_transition_view_svg(model, focus=None, routing='orthogonal') -> str``
    Convenience: build + render to SVG string.
"""

from __future__ import annotations

from typing import Any, Optional, Union

try:
    from boxes import (
        Diagram, Node, Edge, Port,
        InitialPseudostate, JunctionPseudostate,
        ChoicePseudostate, ForkPseudostate, JoinPseudostate,
        FinalState, TerminatePseudostate,
        HistoryPseudostate, EntryPoint, ExitPoint, StateNode,
        OPEN, NONE,
    )
except ImportError as _exc:  # pragma: no cover
    raise ImportError(
        "boxes_view requires the 'boxes' package. Install with:\n"
        "  pip install -e ~/boxes   (or)   poetry run pip install -e ../boxes"
    ) from _exc


def _iter_dict(node: Any):
    """Yield ``(name, dict)`` tuples for every dict with a ``name`` field."""
    if isinstance(node, dict):
        if "name" in node:
            yield node
        for v in node.values():
            yield from _iter_dict(v)
    elif isinstance(node, list):
        for it in node:
            yield from _iter_dict(it)


def _extract_target_from_succession(transition_succession: dict) -> Optional[str]:
    """Pull the target state name out of a ``TransitionSuccession`` dict.

    Structure: ``TransitionSuccession.ownedRelationship[0]
    = ConnectorEndMember.ownedRelatedElement[0] = ConnectorEnd
    .ownedRelationship[0] = OwnedReferenceSubsetting
    .ownedRelatedElement[0] = OwnedFeatureChain.feature
    = FeatureChain.ownedRelationship[*] = OwnedFeatureChaining
    .chainingFeature.names``

    The feature chain may have multiple ``OwnedFeatureChaining`` steps
    for dotted names like ``S2.S3`` — concatenate them with ``.`` to
    preserve the intended target.
    """
    fc = _find_named(transition_succession, "FeatureChain")
    if fc is None:
        # Fallback: pick the single QualifiedName if any.
        qn = _find_named(transition_succession, "QualifiedName")
        if qn and isinstance(qn.get("names"), list) and qn["names"]:
            return qn["names"][-1]
        return None

    # Walk the FeatureChain's ownedRelationship collecting every
    # OwnedFeatureChaining.chainingFeature.names.  Ordered by appearance
    # = outermost-to-innermost segment of the chain.
    def collect_chains(node, parts):
        if isinstance(node, dict):
            if (node.get("name") == "OwnedFeatureChaining"
                    and isinstance(node.get("chainingFeature"), dict)):
                cf = node["chainingFeature"]
                if (cf.get("name") == "QualifiedName"
                        and isinstance(cf.get("names"), list) and cf["names"]):
                    parts.append(cf["names"][-1])
            for v in node.values():
                collect_chains(v, parts)
        elif isinstance(node, list):
            for it in node:
                collect_chains(it, parts)

    parts: list[str] = []
    collect_chains(fc, parts)
    if not parts:
        return None
    return ".".join(parts)


def _extract_accept_trigger(transition_usage: dict) -> Optional[str]:
    """Return the accept-trigger signal name from a TransitionUsage dict."""
    def find_first_named(n, target):
        if isinstance(n, dict):
            if n.get("name") == target:
                return n
            for v in n.values():
                r = find_first_named(v, target)
                if r is not None:
                    return r
        elif isinstance(n, list):
            for it in n:
                r = find_first_named(it, target)
                if r is not None:
                    return r
        return None

    payload = find_first_named(transition_usage, "PayloadParameter")
    if not payload:
        return None
    qn = find_first_named(payload, "QualifiedName")
    if qn and isinstance(qn.get("names"), list) and qn["names"]:
        return qn["names"][-1]
    return None


def _extract_transition_elements(transition_usage: dict) -> dict:
    """Return dict with keys: source, target, trigger, guard, name."""
    info = {"name": None, "source": None, "target": None,
            "trigger": None, "guard": None}
    decl = transition_usage.get("declaration", {})
    decl_decl = decl.get("declaration", {}) if isinstance(decl, dict) else {}
    ident = decl_decl.get("identification", {}) if isinstance(decl_decl, dict) else {}
    if isinstance(ident, dict):
        info["name"] = ident.get("declaredName")

    for rel in transition_usage.get("ownedRelationship", []):
        nm = rel.get("name")
        if nm == "TransitionSourceMember":
            member = rel.get("memberElement", {})
            if isinstance(member, dict):
                names = member.get("names")
                if isinstance(names, list) and names:
                    info["source"] = names[-1]
        elif nm == "TransitionSuccessionMember":
            orel = rel.get("ownedRelatedElement", {})
            tgt = _extract_target_from_succession(orel)
            if tgt:
                info["target"] = tgt
        elif nm == "TriggerActionMember":
            info["trigger"] = _extract_accept_trigger(transition_usage)
        elif nm == "GuardExpressionMember":
            info["guard"] = _extract_guard_expression(rel)
    return info


def _extract_guard_expression(guard_member: dict) -> Optional[str]:
    """Try to recover a short textual form of the guard expression.

    The visitor emits GuardExpressionMember with ownedRelatedExpression
    that nests many levels of operator precedence.  We attempt to find a
    leaf ``QualifiedName`` (a single name like ``guard1``) for use as a
    label snippet.  If the expression is complex we return ``None`` and
    the caller will simply omit the guard from the diagram label.
    """
    def find_first_named(n, target):
        if isinstance(n, dict):
            if n.get("name") == target:
                return n
            for v in n.values():
                r = find_first_named(v, target)
                if r is not None:
                    return r
        elif isinstance(n, list):
            for it in n:
                r = find_first_named(it, target)
                if r is not None:
                    return r
        return None

    qn = find_first_named(guard_member, "QualifiedName")
    if qn and isinstance(qn.get("names"), list) and qn["names"]:
        return qn["names"][-1]
    return None


def _state_action_label(member_name: str) -> str:
    """Visitor ``member_name`` → short label used inside a state box."""
    return {
        "EntryActionMember": "entry",
        "DoActionMember": "do",
        "ExitActionMember": "exit",
    }.get(member_name, "")


def _extract_action_reference(state_action_usage: dict) -> Optional[str]:
    """Try to recover a short action-name reference for entry/do/exit."""
    def find_first_named(n, target):
        if isinstance(n, dict):
            if n.get("name") == target:
                return n
            for v in n.values():
                r = find_first_named(v, target)
                if r is not None:
                    return r
        elif isinstance(n, list):
            for it in n:
                r = find_first_named(it, target)
                if r is not None:
                    return r
        return None

    qn = find_first_named(state_action_usage, "QualifiedName")
    if qn and isinstance(qn.get("names"), list) and qn["names"]:
        return qn["names"][-1]
    return None


def _find_named(node, target):
    """Recursive depth-first walk that returns the *first* dict
    whose ``name`` field equals ``target``.  Used as a convenience
    helper in places where the structure is irregular."""
    if isinstance(node, dict):
        if node.get("name") == target:
            return node
        for v in node.values():
            r = _find_named(v, target)
            if r is not None:
                return r
    elif isinstance(node, list):
        for it in node:
            r = _find_named(it, target)
            if r is not None:
                return r
    return None


def _top_member(item, target):
    """Return the first ``ownedRelationship`` dict at StateBodyItem-level
    whose ``name`` equals *target*, or None.  This is a *shallow* lookup
    that does not descend into sub-bodies (which we need to do
    separately for composite states).
    """
    if not isinstance(item, dict):
        return None
    for r in item.get("ownedRelationship", []):
        if isinstance(r, dict) and r.get("name") == target:
            return r
    return None


def _state_declared_name(state_usage: dict) -> Optional[str]:
    """Extract the declaredName from a StateUsage dict."""
    decl = state_usage.get("declaration", {})
    cur = decl
    while isinstance(cur, dict):
        ident = cur.get("identification")
        if isinstance(ident, dict) and ident.get("declaredName"):
            return ident["declaredName"]
        cur = cur.get("declaration")
    return None


def _collect_state_body(items: list, prefix: str = "",
                        is_parallel: Optional[bool] = None) -> dict:
    """Walk one ``StateDefBody`` / ``StateUsageBody`` item list.

    Returns a dict with keys::

        {
          "parallel": bool,
          "states": [{name, body, parallel, entry, do, exit,
                      states, initial, transitions, composites}, ...],
          "initial": <state name:str>|None,
          "transitions": [ {name, source, target, trigger, guard}, ... ],
          "composites": [ {name, items, ...}, ... ],
          "entry": <action label str|None>,
          "do": <action label str|None>,
          "exit": <action label str|None>,
        }
    """
    result = {
        "parallel": bool(is_parallel),
        "states": [],
        "initial": None,
        "transitions": [],
        "composites": [],
        "entry": None, "do": None, "exit": None,
    }

    for item in items:
        if not isinstance(item, dict):
            continue
        # Check for a top-level Target/Source/Transition member first —
        # they can appear alongside a StateUsage in the same StateBodyItem
        # (the ``accept X then Y`` shorthand tucked in after ``state S;``).
        # The StateUsage branch below intentionally only fires when the
        # only thing in this item is a state declaration, to avoid the
        # shorthand getting swallowed by the StateUsage continue.

        ttu_member = _top_member(item, "TargetTransitionUsageMember")
        if ttu_member is not None:
            ttu = ttu_member.get("ownedRelatedElement", {})
            if isinstance(ttu, dict):
                t = _extract_target_transition_usage(ttu)
                if t is not None:
                    result["transitions"].append(t)
            # The item may ALSO contain a StateUsage for the source —
            # we still want to register that state below, so don't continue.

        ss = _top_member(item, "SourceSuccessionMember")
        if ss is not None:
            t = _extract_accept_then_shorthand(item)
            if t is not None:
                result["transitions"].append(t)

        tu_member = _top_member(item, "TransitionUsageMember")
        if tu_member is not None:
            orel = tu_member.get("ownedRelatedElement", {})
            if isinstance(orel, dict) and orel.get("name") == "TransitionUsage":
                result["transitions"].append(_extract_transition_elements(orel))
            continue

        # entry/do/exit on the enclosing state (only when no other
        # recognizable member is present — these are members of the
        # enclosing region, not of a substate)
        entry_do_exit_handled = False
        for member_key, slot in (("EntryActionMember", "entry"),
                                  ("DoActionMember", "do"),
                                  ("ExitActionMember", "exit")):
            am = _top_member(item, member_key)
            if am is not None:
                orel = am.get("ownedRelatedElement", {})
                ref = _extract_action_reference(orel) if isinstance(orel, dict) else None
                if ref:
                    if prefix and ref.startswith(prefix):
                        ref = ref[len(prefix):]
                    result[slot] = ref
                else:
                    result[slot] = result[slot] or ""
                entry_do_exit_handled = True
                break
        et = _top_member(item, "EntryTransitionMember")
        if et is not None:
            tgt = _extract_target_from_succession(et.get("ownedRelatedElement", {}))
            if tgt:
                result["initial"] = tgt

        bm = _top_member(item, "BehaviorUsageMember")
        if bm is not None:
            orel = bm.get("ownedRelatedElement", {})
            if isinstance(orel, dict) and orel.get("name") == "BehaviorUsageElement":
                su = orel.get("ownedRelationship", {})
                if isinstance(su, dict) and su.get("name") == "StateUsage":
                    sname = _state_declared_name(su)
                    if sname:
                        sub_body = su.get("body", {})
                        sub_def_body = sub_body.get("body", {}) if isinstance(sub_body, dict) else {}
                        sub_part = sub_def_body.get("part", {}) if isinstance(sub_def_body, dict) else {}
                        sub_items = sub_part.get("item", []) if isinstance(sub_part, dict) else []
                        sub_parallel = bool(sub_def_body.get("isParallel")) if isinstance(sub_def_body, dict) else False
                        if sub_items:
                            inner = _collect_state_body(sub_items, prefix=f"{prefix}{sname}.",
                                                        is_parallel=sub_parallel)
                            result["composites"].append({
                                "name": sname,
                                "items": sub_items,
                                **inner,
                            })
                            result["states"].append({"name": sname, **inner})
                        else:
                            result["states"].append({
                                "name": sname,
                                "parallel": False,
                                "entry": None, "do": None, "exit": None,
                                "states": [], "initial": None,
                                "transitions": [], "composites": [],
                            })
                        continue

        # If this item was a pure entry/do/exit member, we already
        # handled it above and there's nothing else to register.
        if entry_do_exit_handled:
            continue
        # entry/do/exit on the enclosing state
        for member_key, slot in (("EntryActionMember", "entry"),
                                  ("DoActionMember", "do"),
                                  ("ExitActionMember", "exit")):
            am = _find_named(item, member_key)
            if am is not None:
                orel = am.get("ownedRelatedElement", {})
                ref = _extract_action_reference(orel) if isinstance(orel, dict) else None
                if ref:
                    # Strip the running prefix already attached to deeper names
                    if prefix and ref.startswith(prefix):
                        ref = ref[len(prefix):]
                    result[slot] = ref
                else:
                    # Empty action — still represent it (e.g. ``entry;``)
                    result[slot] = result[slot] or ""
                break
        # entry; then X;
        et = _find_named(item, "EntryTransitionMember")
        if et is not None:
            tgt = _extract_target_from_succession(et.get("ownedRelatedElement", {}))
            if tgt:
                result["initial"] = tgt
    return result


def _extract_target_transition_usage(ttu: dict) -> Optional[dict]:
    """Extract a transition from a ``TargetTransitionUsage`` shorthand.

    Structure (from inspecting the visitor output):
      ownedRelationship1 = TriggerActionMember (accept trigger)
      ownedRelationship2 = optional GuardExpressionMember
      ownedRelationship3 = optional EffectBehaviorMember
      ownedRelationship4 = TransitionSuccessionMember (target via
        ``TransitionSuccession.ownedRelationship[0]
        .ownedRelatedElement[0].ownedRelationship[0]
        .ownedRelatedElement[0].feature.ownedRelationship[0]
        .chainingFeature.names[-1]``)

    The source state is the lexically previous declared state in the
    enclosing region.  We set ``source=None`` here so the build phase
    can back-fill it from "the most recently emitted state".
    """
    info = {"name": None, "source": None, "target": None,
            "trigger": None, "guard": None}
    rel1 = ttu.get("ownedRelationship1", {})
    if isinstance(rel1, dict) and rel1.get("name") == "TriggerActionMember":
        payload = _find_named(rel1, "PayloadParameter")
        if payload is not None:
            qn = _find_named(payload, "QualifiedName")
            if qn and isinstance(qn.get("names"), list) and qn["names"]:
                info["trigger"] = qn["names"][-1]
    rel2 = ttu.get("ownedRelationship2", {})
    if isinstance(rel2, dict) and rel2.get("name") == "GuardExpressionMember":
        info["guard"] = _extract_guard_expression(rel2)
    rel4 = ttu.get("ownedRelationship4", {})
    if isinstance(rel4, dict) and rel4.get("name") == "TransitionSuccessionMember":
        orel = rel4.get("ownedRelatedElement", {})
        tgt = _extract_target_from_succession(orel)
        if tgt:
            info["target"] = tgt
    if info["target"] is None:
        return None
    return info


def _extract_accept_then_shorthand(state_body_item: dict) -> Optional[dict]:
    """Convert the ``accept X then Y`` shorthand into a TransitionUsage-like dict.

    The shorthand succession lives in StateBodyItem as:
      SourceSuccessionMember → SourceSuccession (with a source behavior usage,
      usually an unnamed accept action) ... then GuardedTargetSuccession with
      the target name.  In practice this is rare in real models — most
    writers use named transitions.  If we cannot recover a clean (source,
    target, trigger) triple, return None.
    """
    # Locate the accept trigger via TriggerActionMember / AcceptActionUsage
    trigger = None
    def find_first_named(n, target):
        if isinstance(n, dict):
            if n.get("name") == target:
                return n
            for v in n.values():
                r = find_first_named(v, target)
                if r is not None:
                    return r
        elif isinstance(n, list):
            for it in n:
                r = find_first_named(it, target)
                if r is not None:
                    return r
        return None
    payload = find_first_named(state_body_item, "PayloadParameter")
    if payload:
        qn = find_first_named(payload, "QualifiedName")
        if qn and isinstance(qn.get("names"), list) and qn["names"]:
            trigger = qn["names"][-1]

    # Target: SuccessionFlow or QualifiedName on GuardedTargetSuccession
    target = None
    gts = find_first_named(state_body_item, "GuardedTargetSuccession")
    if gts is not None:
        tgt_qn = find_first_named(gts, "QualifiedName")
        if tgt_qn and isinstance(tgt_qn.get("names"), list) and tgt_qn["names"]:
            target = tgt_qn["names"][-1]

    # Source is the closest declared state in the enclosing region; we
    # don't know it locally here, so leave it as None and let the caller
    # resolve it as "previous declared state".  For now return None unless
    # both trigger and target are present.
    if trigger is not None and target is not None:
        return {"name": None, "source": None, "target": target,
                "trigger": trigger, "guard": None}
    return None


def _collect_state_machine(visit_dict: dict) -> list:
    """Return a list of state-machine descriptors.

    Each descriptor is a dict::

        {
          "name": <state def name>,
          "parallel": bool,
          "states": [{name, body, parallel, ...}, ...],
          "initial": <state name:str>|None,
          "transitions": [{name, source, target, trigger, guard}, ...],
          "composites": [{name, items, ...}, ...],
        }
    """
    machines: list[dict] = []
    for node in _iter_dict(visit_dict):
        if node.get("name") != "StateDefinition":
            continue
        decl = node.get("declaration", {})
        sm_name = None
        if isinstance(decl, dict):
            ident = decl.get("identification")
            if isinstance(ident, dict):
                sm_name = ident.get("declaredName")
        body = node.get("body", {})
        part = body.get("part", {}) if isinstance(body, dict) else {}
        items = part.get("item", []) if isinstance(part, dict) else []
        sm_parallel = bool(body.get("isParallel")) if isinstance(body, dict) else False

        sm = {
            "name": sm_name,
            "parallel": sm_parallel,
            "states": [],
            "initial": None,
            "transitions": [],
            "composites": [],
        }
        sm.update(_collect_state_body(items, is_parallel=sm_parallel))
        machines.append(sm)
    return machines


def as_state_transition_view_boxes(
    model: Union[str, "sysmlpy.Model", dict],
    focus: Optional[str] = None,
    include_legend: bool = False,
):
    """Build a ``boxes.Diagram`` from a parsed SysML state machine.

    Parameters
    ----------
    model
        Either:
        - raw SysML text (will be parsed via ``load_grammar``)
        - a dict returned by ``sysmlpy.load_grammar()``
        - a ``sysmlpy.Model`` object returned by ``sysmlpy.loads()``
    focus
        Name of the ``state def`` to render. If None and only one state def
        is present, it is chosen automatically; otherwise the first is used
        (and a note is printed when multiple are present).
    include_legend
        Currently unused; reserved for a future ASCII legend.

    Returns
    -------
    boxes.Diagram
    """
    import sysmlpy

    if isinstance(model, str):
        visit_dict = sysmlpy.load_grammar(model)
    elif isinstance(model, dict):
        visit_dict = model
    elif hasattr(model, "children"):  # parsed Model
        # Re-parse from dump() to obtain the visitor dict.
        visit_dict = sysmlpy.load_grammar(model.dump())
    else:
        raise TypeError(f"Unsupported model type: {type(model).__name__}")

    machines = _collect_state_machine(visit_dict)
    if not machines:
        return Diagram()

    if focus is not None:
        candidates = [m for m in machines if m["name"] == focus]
        if not candidates:
            raise ValueError(f"No state def named {focus!r}; found {[m['name'] for m in machines]}")
        sm = candidates[0]
    elif len(machines) == 1:
        sm = machines[0]
    else:
        sm = machines[0]
        print(f"[boxes_view] multiple state defs found: {[m['name'] for m in machines]}; rendering {sm['name']!r}. Pass focus= to choose.")

    d = Diagram()
    state_nodes: dict[str, Node] = {}
    # Cache the implicit "done" final-state node per container namespace so
    # multiple incoming transitions into `done` reuse one bullseye.
    final_cache: dict[str, object] = {}

    def _state_attributes(level: dict) -> list:
        attrs = []
        if level.get("entry") is not None:
            attrs.append(f"entry / {level['entry']}" if level["entry"] else "entry /")
        if level.get("do") is not None:
            attrs.append(f"do / {level['do']}" if level["do"] else "do /")
        if level.get("exit") is not None:
            attrs.append(f"exit / {level['exit']}" if level["exit"] else "exit /")
        return attrs

    def _build(level: dict, namespace: str):
        """Emit states + transitions for one level of the state machine.

        Composite (nested) states are emitted as <StateNode> instances and
        then their sub-states and transitions are emitted as siblings,
        each name-qualified by the parent state, with simple, dotted
        reference tracking.  Transition endpoints that resolve via
        unqualified NAME are matched locally; if not found locally they
        fall back to being prefixed with the parent namespace.
        """
        composite_names = {comp["name"] for comp in level.get("composites", [])}

        # States list can be either plain names (strings) or dicts with
        # entry/do/exit/parallel metadata — handle both shapes.
        plain_states = []
        for state in level["states"]:
            if isinstance(state, dict):
                plain_states.append(state)
            else:
                plain_states.append({"name": state, "parallel": False})

        # Emit composite states and recurse
        for comp in level.get("composites", []):
            comp_full = comp["name"] if not namespace else f"{namespace}.{comp['name']}"
            attrs = _state_attributes(comp)
            if comp.get("parallel"):
                # indicate parallel composition by adding a «parallel»
                # stereotype alongside the default «state» stereotype.
                state_nodes[comp_full] = d.add_node(
                    comp["name"],
                    stereotypes=["state", "parallel"],
                    attributes=attrs, rounded=True,
                )
            else:
                state_nodes[comp_full] = d.add_node(
                    comp["name"], stereotypes=["state"],
                    attributes=attrs, rounded=True,
                )
            _build(comp, namespace=comp_full)

        # Emit plain (non-composite) states so they're registered.
        # Prefer the dict form for entry/do/exit attribute population.
        for state in plain_states:
            sname = state["name"]
            if sname in composite_names:
                continue  # already emitted as a composite
            full = sname if not namespace else f"{namespace}.{sname}"
            attrs = _state_attributes(state)
            state_nodes[full] = d.add_node(
                sname, stereotypes=["state"], attributes=attrs, rounded=True,
            )

    _build(sm, namespace="")

    def _resolve(name: str, namespace: str):
        """Try resolving a transition endpoint to a registered node.

        First try the bare name; then try namespace-qualified name; then
        walk up the namespace chain.  Special-case `done`, which is the
        SysML v2 implicit final state (see spec §7.18) — we synthesize a
        bullseye final state node on first encounter in each container
        namespace.
        """
        if name == "done":
            # Synthesize / reuse a final-state bullseye for this region.
            key = namespace or "_top"
            if key not in final_cache:
                final_cache[key] = d.add_final_state()
            return final_cache[key]
        if name in state_nodes:
            return state_nodes[name]
        if namespace:
            full = f"{namespace}.{name}"
            if full in state_nodes:
                return state_nodes[full]
            parts = namespace.split(".")
            for i in range(len(parts) - 1, 0, -1):
                candidate = f"{'.'.join(parts[:i])}.{name}"
                if candidate in state_nodes:
                    return state_nodes[candidate]
        return None

    def _emit_transitions(level: dict, namespace: str):
        initial_node = None
        # Back-fill implicit-source transitions from the most-recently
        # declared state in this region (SysML v2 ``accept X then Y``
        # shorthand attaches the transition to the preceding ``state X;``).
        most_recent_state = None
        for s in level["states"]:
            sname = s["name"] if isinstance(s, dict) else s
            full = sname if not namespace else f"{namespace}.{sname}"
            if full in state_nodes:
                most_recent_state = state_nodes[full]

        if level["initial"] is not None:
            initial_node = d.add_initial()
            tgt = _resolve(level["initial"], namespace)
            if tgt is not None:
                d.add_edge(initial_node, tgt, source_style=NONE, target_style=NONE)
            else:
                print(f"[boxes_view] initial target {level['initial']!r} not resolvable from namespace {namespace!r}")
        for tr in level["transitions"]:
            if tr["source"] is None:
                # Implicit source = most-recent declared state in region
                src = most_recent_state
            else:
                src = _resolve(tr["source"], namespace)
            dst = _resolve(tr["target"], namespace)
            if src is None or dst is None:
                print(f"[boxes_view] transition {tr.get('name')!r}: missing endpoint (src={tr['source']}, dst={tr['target']}) [ns={namespace!r}]")
                continue
            # Compose trigger and guard into the edge label.
            label_parts = []
            if tr.get("trigger"):
                label_parts.append(tr["trigger"])
            if tr.get("guard"):
                label_parts.append(f"[{tr['guard']}]")
            if tr.get("name") and not tr.get("trigger"):
                label_parts.append(tr["name"])
            label = " ".join(label_parts) if label_parts else None
            d.add_edge(src, dst, target_style=OPEN, label=label)
        for comp in level.get("composites", []):
            comp_full = comp["name"] if not namespace else f"{namespace}.{comp['name']}"
            _emit_transitions(comp, namespace=comp_full)

    _emit_transitions(sm, namespace="")

    return d


def render_state_transition_view(
    model: Union[str, "sysmlpy.Model", dict],
    focus: Optional[str] = None,
    routing: str = "orthogonal",
    **layout_kw,
) -> str:
    """Convenience: build + render to terminal braille string."""
    d = as_state_transition_view_boxes(model, focus=focus)
    return d.render(routing=routing, **layout_kw)


def render_state_transition_view_svg(
    model: Union[str, "sysmlpy.Model", dict],
    focus: Optional[str] = None,
    routing: str = "orthogonal",
    scale: float = 1.5,
    **layout_kw,
) -> str:
    """Convenience: build + render to SVG string."""
    d = as_state_transition_view_boxes(model, focus=focus)
    return d.render_svg(routing=routing, scale=scale, **layout_kw)


__all__ = [
    "as_state_transition_view_boxes",
    "render_state_transition_view",
    "render_state_transition_view_svg",
    "InitialPseudostate", "JunctionPseudostate",
    "ChoicePseudostate", "ForkPseudostate", "JoinPseudostate",
    "FinalState", "TerminatePseudostate",
    "HistoryPseudostate", "EntryPoint", "ExitPoint", "StateNode",
]