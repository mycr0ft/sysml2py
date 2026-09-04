#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Adapter that renders a sysmlpy state machine as a `diagramboxes`
Diagram. (The `boxes` package was renamed to `diagramboxes` in v0.3.0
to avoid a PyPI name collision.)

Walks the visitor dict produced by :func:`sysmlpy.load_grammar` to find
StateDefinition / StateUsage / TransitionUsage / EntryTransitionMember nodes
and emits a diagramboxes Diagram with:

- rounded ``Node`` (stereotype ``«state»``) for each ``state`` member
- a filled ``StartNode`` (initial pseudostate) for each ``entry; then X;``
- an ``Edge`` from the initial pseudostate to the target state (no arrowhead)
- an ``Edge`` between states for each ``transition X first A accept B then C``
  with the trigger name as the label

The diagramboxes pseudostate shapes already match UML/SysML notation:
``StartNode`` = filled circle (initial), ``DoneNode`` = bullseye (final),
``DecisionNode`` = diamond (choice), ``ForkJoinNode`` = thick bar (fork/join),
``TerminateNode`` = X-in-circle (terminate). These are imported and re-aliased
as the state-machine pseudostates to make intent explicit in client code.

Public API
----------
``as_state_transition_view_boxes(model, focus=None) -> diagramboxes.Diagram``
    Build a Diagram from a parsed model (or a SysML text string).
``render_state_transition_view(model, focus=None, routing='orthogonal') -> str``
    Convenience: build + render to terminal braille string.
``render_state_transition_view_svg(model, focus=None, routing='orthogonal') -> str``
    Convenience: build + render to SVG string.
"""

from __future__ import annotations

from typing import Any, Optional, Union

try:
    from diagramboxes import (
        Diagram, Node, Edge, Port,
        InitialPseudostate, JunctionPseudostate,
        ChoicePseudostate, ForkPseudostate, JoinPseudostate,
        FinalState, TerminatePseudostate,
        HistoryPseudostate, EntryPoint, ExitPoint, StateNode,
        OPEN, NONE, DASHED,
    )
except ImportError as _exc:  # pragma: no cover
    raise ImportError(
        "boxes_view requires the 'diagramboxes' package. Install with:\n"
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


def _state_body_items(state_def_like: dict) -> tuple:
    """Return (items, is_parallel) for a StateDefinition *or* a composite
    StateUsage. The two have the same body shape: ``.body.part.item`` and
    ``.body.isParallel``. The StateUsage wraps its StateDefBody one level
    deeper — ``.body.body.part.item`` — so we handle both.

    Returns ([], False) if the body structure cannot be found.
    """
    body = state_def_like.get("body", {})
    # StateDefinition: body.part.item / body.isParallel
    if isinstance(body, dict) and "part" in body:
        part = body.get("part") or {}
        items = part.get("item", []) if isinstance(part, dict) else []
        is_parallel = bool(body.get("isParallel")) if isinstance(body, dict) else False
        return items, is_parallel
    # StateUsage: body.body.part.item / body.body.isParallel
    inner = body.get("body", {}) if isinstance(body, dict) else {}
    if isinstance(inner, dict) and "part" in inner:
        part = inner.get("part") or {}
        items = part.get("item", []) if isinstance(part, dict) else []
        is_parallel = bool(inner.get("isParallel")) if isinstance(inner, dict) else False
        return items, is_parallel
    return [], False


def _collect_state_machine(visit_dict: dict) -> list:
    """Return a list of state-machine descriptors.

    Each descriptor is a dict::

        {
          "name": <state def / state usage name>,
          "parallel": bool,
          "states": [{name, body, parallel, ...}, ...],
          "initial": <state name:str>|None,
          "transitions": [{name, source, target, trigger, guard}, ...],
          "composites": [{name, items, ...}, ...],
        }

    Both top-level ``state def X { … }`` (StateDefinition) and top-level
    ``state X { … }`` (StateUsage with a body) are recognized, so models
    that put their state machine at package level (the common pattern
    used by the INCOSE flashlight / OMG Simple State Example) work too.

    Nested StateUsages inside another StateDefinition/StateUsage — the
    substates — are *not* emitted as standalone machines; they are
    handled by the recursive ``_collect_state_body`` walk.
    """
    machines: list[dict] = []
    # Track IDs of every StateUsage dict nested inside an already-collected
    # machine — so we don't duplicate them as their own top-level machines.
    nested_state_usage_ids: set = set()

    def _mark_nested_state_usages(node_obj):
        if isinstance(node_obj, dict):
            if node_obj.get("name") == "StateUsage":
                nested_state_usage_ids.add(id(node_obj))
            for v in node_obj.values():
                _mark_nested_state_usages(v)
        elif isinstance(node_obj, list):
            for it in node_obj:
                _mark_nested_state_usages(it)

    for node in _iter_dict(visit_dict):
        nm = node.get("name")
        if nm not in ("StateDefinition", "StateUsage"):
            continue
        if id(node) in nested_state_usage_ids:
            continue
        items, is_parallel = _state_body_items(node)
        if nm == "StateUsage" and not items:
            continue

        decl = node.get("declaration", {})
        sm_name = None
        # Walk the declaration chain looking for an identification
        cur = decl
        while isinstance(cur, dict) and sm_name is None:
            ident = cur.get("identification")
            if isinstance(ident, dict) and ident.get("declaredName"):
                sm_name = ident["declaredName"]
                break
            cur = cur.get("declaration")
            if cur is None or not isinstance(cur, dict):
                break

        sm = {
            "name": sm_name,
            "parallel": is_parallel,
            "states": [],
            "initial": None,
            "transitions": [],
            "composites": [],
        }
        sm.update(_collect_state_body(items, is_parallel=is_parallel))
        # Mark every StateUsage reachable from this machine's items tree
        # as nested, so the outer _iter_dict pass skips them when it
        # surfaces them later.
        _mark_nested_state_usages(items)
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

    def _build(level: dict, namespace: str, parent_node=None):
        """Emit states + transitions for one level of the state machine.

        Composite (nested) states are emitted as <StateNode> instances
        *nested inside their parent node* (diagramboxes v0.4.0 composite
        structure), and their sub-states and transitions are emitted as
        children of the composite.  Names stay namespace-qualified in
        ``state_nodes`` for resolution.  Transition endpoints that
        resolve via unqualified NAME are matched locally; if not found
        locally they fall back to being prefixed with the parent
        namespace.
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
                    parent=parent_node,
                )
            else:
                state_nodes[comp_full] = d.add_node(
                    comp["name"], stereotypes=["state"],
                    attributes=attrs, rounded=True,
                    parent=parent_node,
                )
            _build(comp, namespace=comp_full, parent_node=state_nodes[comp_full])

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
                parent=parent_node,
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
            # Synthesize / reuse a final-state bullseye for this region,
            # nested inside the region's composite state (v0.4.0).
            key = namespace or "_top"
            if key not in final_cache:
                region_node = state_nodes.get(namespace)
                final_cache[key] = d.add_final_state(parent=region_node)
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
        # Last-segment fallback (diagramboxes v0.4.0 nesting): an
        # unqualified name may refer to a state nested inside a
        # composite declared in this region (e.g. `transition Running
        # then Stopped;` where Stopped lives inside Running).
        cands = [full for full in state_nodes if full.endswith("." + name)]
        if len(cands) == 1:
            return state_nodes[cands[0]]
        if len(cands) > 1:
            if namespace:
                pref = [c for c in cands if c.startswith(namespace + ".")]
                cands = pref or cands
            print(f"[boxes_view] ambiguous endpoint {name!r}: {cands}; using {cands[0]!r}")
            return state_nodes[cands[0]]
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
            region_node = state_nodes.get(namespace)
            initial_node = d.add_initial(parent=region_node)
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


def as_interconnection_view_boxes(
    model: Union[str, "sysmlpy.Model", dict],
    focus: Optional[str] = None,
    include_external: bool = False,
) -> "Diagram":
    """Build a boxes (diagramboxes) interconnection diagram from a model.

    Renders part usages as boxes, their boundary ports as small port
    markers (``node.add_port``), and ``connection`` usages as port-to-port
    edges (Z-routed by the layout engine).  Endpoints chained through
    ports (``connection clutch connect engine.powerOut to
    drivetrain.powerIn``) create the ports; plain connections
    (``connect engine to drivetrain``) become direct node-to-node edges.

    Parameters
    ----------
    model : str, sysmlpy.Model, or dict
        SysML v2 text, a loaded Model, or a parsed definition dict.
    focus : str, optional
        Restrict the view to connections touching this part.
    include_external : bool, optional
        If True (default False), parts outside the focus scope that
        still participate in connections are included.

    Returns
    -------
    diagramboxes.Diagram
    """
    from sysmlpy.plantuml import _extract_connections

    import sysmlpy as _sysmlpy
    if isinstance(model, str):
        model = _sysmlpy.loads(model)
    elif isinstance(model, dict):
        model = _sysmlpy.loads(_sysmlpy.dump(model))

    def _parts_from(model):
        if hasattr(model, "all") and callable(model.all):
            try:
                return [p for p in model.all("part") if not p.is_definition]
            except Exception:
                return []
        return []

    parts = _parts_from(model)
    by_name = {getattr(p, "name", None): p for p in parts if getattr(p, "name", None)}

    conns = []
    for from_names, to_names, cname in _extract_connections(model):
        if not from_names or not to_names:
            continue
        if focus is not None:
            focus_root = focus.split(".")[0]
            ends = (from_names[0], to_names[0])
            if focus_root not in ends:
                continue
        conns.append((from_names, to_names, cname))

    if not conns:
        raise ValueError(
            "as_interconnection_view_boxes: no connections found"
            + (f" touching {focus!r}" if focus else "")
        )

    included: set = set()
    for from_names, to_names, _ in conns:
        included.add(from_names[0])
        included.add(to_names[0])

    d = Diagram()
    nodes: dict[str, Node] = {}

    for name in sorted(included):
        part = by_name.get(name)
        stereotypes = ["part"]
        attributes = []
        if part is not None:
            typed = getattr(part, "typed_by_name", None)
            if typed:
                stereotypes.append(typed.split("::")[-1])
            for att in (getattr(part, "attributes", None) or []):
                aname = getattr(att, "name", None)
                if aname:
                    attributes.append(f"+ {aname}")
        nodes[name] = d.add_node(name, stereotypes=stereotypes,
                                 attributes=attributes, rounded=True)

    # Assign each chained endpoint port to a side: source-side ports sit
    # on the right of the source box, target-side ports on the left of
    # the target box.  A port used in both roles defaults to the right.
    port_of: dict[tuple, object] = {}

    def _port(node: Node, label: str, is_source: bool):
        if not label:
            return None
        key = (node.name, label)
        if key in port_of:
            return port_of[key]
        side = "right" if is_source else "left"
        same = [p for p in node.ports if p.side == side]
        offset = (len(same) + 1) / 4.0 if same else None
        if offset is not None and offset > 1.0:
            offset = 0.5
        p = node.add_port(label, side=side,
                          offset=None if len(same) == 0 else offset,
                          label_inside=True)
        port_of[key] = p
        return p

    for from_names, to_names, cname in conns:
        src = nodes[from_names[0]]
        dst = nodes[to_names[0]]
        sp = _port(src, from_names[1] if len(from_names) > 1 else "", True)
        tp = _port(dst, to_names[1] if len(to_names) > 1 else "", False)
        if sp is not None and tp is not None:
            d.add_edge(src, dst, source_port=sp, target_port=tp,
                       label=cname, target_style=OPEN)
        else:
            d.add_edge(src, dst, label=cname, target_style=OPEN)

    return d


def render_interconnection_view_boxes(
    model: Union[str, "sysmlpy.Model", dict],
    focus: Optional[str] = None,
    routing: str = "orthogonal",
    **layout_kw,
) -> str:
    """Convenience: build + render the boxes interconnection view (braille)."""
    d = as_interconnection_view_boxes(model, focus=focus)
    return d.render(routing=routing, **layout_kw)


def render_interconnection_view_boxes_svg(
    model: Union[str, "sysmlpy.Model", dict],
    focus: Optional[str] = None,
    routing: str = "orthogonal",
    scale: float = 1.5,
    **layout_kw,
) -> str:
    """Convenience: build + render the boxes interconnection view as SVG."""
    d = as_interconnection_view_boxes(model, focus=focus)
    return d.render_svg(routing=routing, scale=scale, **layout_kw)

# ---------------------------------------------------------------------------
# Action flow view (afv) via boxes
# ---------------------------------------------------------------------------

def _afv_kids(value):
    """Normalize a grammar ``children`` value to a list.

    Grammar objects store ``children`` as a list, a single child
    object, or None depending on cardinality — this hides that from
    the walkers below.
    """
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _afv_flow_end(end_member):
    """``(owner, param)`` from one FlowEndMember of a flow grammar.

    The flow-end grammar nests as::

        FlowEndMember → FlowEnd
            → FlowEndSubsetting → QualifiedName(names)     # owning feature
            → FlowFeatureMember → FlowFeature
                  → FlowRedefinition → QualifiedName(names)  # parameter

    Either part may be absent (e.g. ``flow t to inject.i`` has a
    subsetting name but no parameter chain on the source end).
    """
    owner = param = None
    for fe in _afv_kids(getattr(end_member, "children", None)):
        if fe.__class__.__name__ != "FlowEnd":
            continue
        for sub in _afv_kids(getattr(fe, "children", None)):
            cname = sub.__class__.__name__
            if cname == "FlowEndSubsetting":
                for q in _afv_kids(getattr(sub, "children", None)):
                    if q.__class__.__name__ == "QualifiedName" and getattr(q, "names", None):
                        owner = list(q.names)
            elif cname == "FlowFeatureMember":
                for ff in _afv_kids(getattr(sub, "children", None)):
                    for fr in _afv_kids(getattr(ff, "children", None)):
                        for q in _afv_kids(getattr(fr, "children", None)):
                            if q.__class__.__name__ == "QualifiedName" and getattr(q, "names", None):
                                param = list(q.names)
    return owner, param


def _afv_flow_grammar_ends(flow_grammar):
    """``((owner, param), (owner, param))`` from a FlowConnectionUsage grammar."""
    decl = getattr(flow_grammar, "declaration", None)
    members = _afv_kids(getattr(decl, "children", None))
    ends = [_afv_flow_end(m) for m in members[1:]]
    if len(ends) >= 2:
        return ends[0], ends[1]
    return None, None


def _afv_action_params(grammar_obj):
    """``[(name, direction)]`` declared parameters of an action def/usage.

    Walks the action body grammar
    (``body → ActionBodyItem → NonOccurrenceUsageMember →
    NonOccurrenceUsageElement → <usage>.prefix.direction`` +
    ``.declaration.declaration.identification.declaredName``).
    Direction comes from ``FeatureDirection`` (isIn/isOut/isInOut).
    """
    body = getattr(grammar_obj, "body", None)
    params = []
    for item in _afv_kids(getattr(body, "children", None)):
        for member in _afv_kids(getattr(item, "children", None)):
            for elem in _afv_kids(getattr(member, "children", None)):
                for ref in _afv_kids(getattr(elem, "children", None)):
                    decl = getattr(ref, "declaration", None)
                    fd = getattr(decl, "declaration", None) if decl is not None else None
                    if fd is None or fd.__class__.__name__ != "FeatureDeclaration":
                        continue
                    ident = getattr(fd, "identification", None)
                    name = getattr(ident, "declaredName", None) if ident is not None else None
                    if not name:
                        continue
                    direction = getattr(getattr(ref, "prefix", None), "direction", None)
                    side = ("in" if getattr(direction, "isIn", None) else
                            "out" if getattr(direction, "isOut", None) else
                            "inout" if getattr(direction, "isInOut", None) else None)
                    params.append((name, side))
    return params


def _afv_flows_in_body(grammar_obj, out, depth=0):
    """Recursively collect FlowConnectionUsage/Definition grammar objects."""
    if depth > 24:
        return
    body = getattr(grammar_obj, "body", None)
    if body is not None and body is not grammar_obj:
        _afv_flows_in_body(body, out, depth + 1)
    for child in _afv_kids(getattr(grammar_obj, "children", None)):
        if child.__class__.__name__ in ("FlowConnectionUsage", "FlowConnectionDefinition"):
            out.append(child)
        else:
            _afv_flows_in_body(child, out, depth + 1)


def _afv_successions_in_body(grammar_obj, out, depth=0):
    """Recursively collect ``Succession`` grammar objects."""
    if depth > 24:
        return
    body = getattr(grammar_obj, "body", None)
    if body is not None and body is not grammar_obj:
        _afv_successions_in_body(body, out, depth + 1)
    for child in _afv_kids(getattr(grammar_obj, "children", None)):
        if child.__class__.__name__ == "Succession":
            out.append(child)
        else:
            _afv_successions_in_body(child, out, depth + 1)


def _afv_succession_ends(succ):
    """``[names]`` — OwnedReferenceSubsetting name lists of both ends."""
    ends = []
    for mem in _afv_kids(getattr(succ, "children", None)):
        for end in _afv_kids(getattr(mem, "children", None)):
            for ref in _afv_kids(getattr(end, "children", None)):
                if ref.__class__.__name__ != "OwnedReferenceSubsetting":
                    continue
                seg = []
                rf = getattr(ref, "referencedFeature", None)
                if rf is not None and getattr(rf, "names", None):
                    seg.extend(rf.names)
                for chain in (getattr(ref, "elements", None) or []):
                    for oc in _afv_kids(getattr(chain, "children", None)):
                        cf = getattr(oc, "chainingFeature", None)
                        if cf is not None and getattr(cf, "names", None):
                            seg.extend(cf.names)
                if seg:
                    ends.append(seg)
    return ends


def _afv_uuid_like(name):
    """True for anonymous-element UUID names (suppress as edge labels)."""
    if not name:
        return True
    return len(name) == 36 and name.count("-") == 4 and all(
        c in "0123456789abcdef" for c in name.replace("-", ""))


def as_action_flow_view_boxes(
    model: Union[str, "sysmlpy.Model", dict],
    focus: Optional[str] = None,
) -> "Diagram":
    """Build a boxes (diagramboxes) action flow diagram from a model.

    Renders action usages as boxes («action», or «action def» when the
    box is a definition that contains structure), declared action
    parameters as boundary ports (``in`` on the left, ``out`` on the
    right), and flow connections as edges — port-to-port when an end
    chains through a parameter (``flow providePower.torque to
    injectFuel.fuelCommand``), direct box-to-box otherwise.  Actions
    nested in an inline action usage or an action definition render as
    composite children (diagramboxes v0.4.0 nesting).

    Definitions without nested actions or internal flows are not drawn
    as boxes — their parameters surface on the typed usage's ports.

    Successions between nested actions
    (``succession s1 first torque then inject;``) render as dashed
    edges (``..>`` per the official notation).

    Parameters
    ----------
    model : str, sysmlpy.Model, or dict
        SysML v2 text, a loaded Model, or a parsed definition dict.
    focus : str, optional
        Restrict to the subtree of this action (def or usage) plus any
        flows touching its actions (partners included).

    Returns
    -------
    diagramboxes.Diagram
    """
    import sysmlpy as _sysmlpy

    if isinstance(model, str):
        model = _sysmlpy.loads(model)
    elif isinstance(model, dict):
        model = _sysmlpy.loads(_sysmlpy.dump(model))

    if not hasattr(model, "all"):
        raise TypeError(f"Unsupported model type: {type(model).__name__}")

    # ---- 1. collect actions with their nearest action ancestor -------
    usages = []   # (element, parent_action_element_or_None)
    defs = []     # action definitions
    order = {}    # element id -> creation order (stable node placement)

    def _walk(el, chain):
        st = getattr(el, "sysml_type", None)
        if st == "action":
            if getattr(el, "is_definition", False):
                defs.append(el)
                order[id(el)] = len(order)
            else:
                parent = next((a for a in reversed(chain)
                               if getattr(a, "sysml_type", None) == "action"), None)
                usages.append((el, parent))
                order[id(el)] = len(order)
        for c in (getattr(el, "children", None) or []):
            _walk(c, chain + [el])

    _walk(model, [])

    if not usages and not defs:
        raise ValueError("as_action_flow_view_boxes: no actions found")

    # ---- 2. collect flows (usage-level + grammar-level with container) --
    flows = []    # (flow_grammar, flow_name, container_element_or_None)
    successions = []   # (Succession grammar, name, container_element)
    visited_ids = set()

    def _scan(el):
        eid = id(el)
        if eid in visited_ids:
            return
        visited_ids.add(eid)

        g = getattr(el, "grammar", None)
        if getattr(el, "sysml_type", "") == "flow" and g is not None:
            flows.append((g, getattr(el, "name", None), None))
        if g is not None:
            found = []
            _afv_flows_in_body(g, found)
            for fgo in found:
                if id(fgo) not in visited_ids:
                    visited_ids.add(id(fgo))
                    flows.append((fgo, None, el))
            succs = []
            _afv_successions_in_body(g, succs)
            for so in succs:
                if id(so) not in visited_ids:
                    visited_ids.add(id(so))
                    successions.append((so, getattr(so, "name", None), el))
        for c in (getattr(el, "children", None) or []):
            _scan(c)

    for child in (getattr(model, "children", None) or []):
        _scan(child)

    # ---- 3. resolve endpoints: name -> action element -------------------
    action_by_name = {}
    for el in defs:
        action_by_name.setdefault(getattr(el, "name", None), el)
    for el, _p in usages:
        action_by_name.setdefault(getattr(el, "name", None), el)

    param_names = {}   # element id -> {param name: direction}
    for el in defs + [u for u, _ in usages]:
        g = getattr(el, "grammar", None)
        if g is not None:
            param_names[id(el)] = {n: side for n, side in _afv_action_params(g)}
    # typed usages inherit their def's parameters
    typed_def = {}
    for el, _p in usages:
        tn = getattr(el, "typed_by_name", None)
        if tn and not param_names.get(id(el)):
            base = tn.split("::")[-1]
            de = action_by_name.get(base)
            if de is not None and getattr(de, "is_definition", False):
                typed_def[id(el)] = de
                if id(de) not in param_names:
                    dg = getattr(de, "grammar", None)
                    param_names[id(de)] = ({n: s for n, s in _afv_action_params(dg)}
                                           if dg is not None else {})

    def _resolve_end(owner, param, container):
        """Map an (owner, param) flow end to (element, port_name) or None."""
        if owner:
            key = ".".join(owner)
            el = action_by_name.get(key) or action_by_name.get(owner[-1])
            if el is not None:
                return el, (param[-1] if param else None)
            # owner may name a parameter of the enclosing def/usage
            if container is not None:
                cn = param_names.get(id(container)) or {}
                if owner[0] in cn:
                    return container, owner[0]
        elif container is not None and param:
            # bare parameter reference of the enclosing context
            cn = param_names.get(id(container)) or {}
            if param[-1] in cn:
                return container, param[-1]
        return None, None

    resolved = []   # (from_elem, from_port, to_elem, to_port, label[, dashed])
    for fgo, fname, container in flows:
        ends = _afv_flow_grammar_ends(fgo)
        if not ends or ends[0] is None or ends[1] is None:
            continue
        ends_resolved = []
        for owner, param in ends:
            ends_resolved.append(_resolve_end(owner, param, container))
        (fe, fport), (te, tport) = ends_resolved
        if fe is None or te is None:
            continue  # unresolvable ends are simply not drawn
        if fe is te:
            continue
        # Skip container-to-own-child flows: they would re-anchor to a
        # self edge in the nested layout (e.g. a def's parameter port
        # feeding its own nested action).
        if container is not None and (fe is container or te is container):
            continue
        label = None if _afv_uuid_like(fname) else fname
        resolved.append((fe, fport, te, tport, label))

    for so, sname, container in successions:
        if sname is None:
            ident = getattr(getattr(getattr(so, "declaration", None),
                                    "declaration", None),
                            "identification", None)
            sname = getattr(ident, "declaredName", None)
        ends = _afv_succession_ends(so)
        if len(ends) < 2:
            continue
        ends_resolved = []
        for owner in ends[:2]:
            ends_resolved.append(_resolve_end(owner, None, container))
        (fe, fport), (te, tport) = ends_resolved
        if fe is None or te is None or fe is te:
            continue
        if container is not None and (fe is container or te is container):
            continue
        label = None if _afv_uuid_like(sname) else sname
        resolved.append((fe, fport, te, tport, label, True))

    # ---- 3b. which definitions need a box ------------------------------
    parents_needed = {id(p) for _e, p in usages if p is not None}
    containers_needed = {id(c) for _fgo, _n, c in flows if c is not None}
    defs_to_draw = [d for d in defs
                    if id(d) in parents_needed or id(d) in containers_needed]

    # ---- 3c. focus filter ----------------------------------------------
    keep_ids = None
    if focus is not None:
        focus_el = action_by_name.get(focus)
        if focus_el is None:
            raise ValueError(
                f"as_action_flow_view_boxes: no action named {focus!r}; "
                f"found {sorted(n for n in action_by_name if n)}")
        # Subtree of the focus action: itself plus every usage whose
        # parent chain (nested actions / owning def) reaches it.
        parent_chain = {}   # element id -> parent element id
        for el, parent in usages:
            if parent is not None:
                parent_chain[id(el)] = id(parent)
        subtree = {id(focus_el)}
        for el, _parent in usages:
            walk = parent_chain.get(id(el))
            while walk is not None:
                if walk == id(focus_el):
                    subtree.add(id(el))
                    break
                walk = parent_chain.get(walk)
        keep_ids = subtree

    # ---- 4. build nodes --------------------------------------------------
    d = Diagram()
    nodes = {}         # element id -> Node

    def _stereo(el, is_def):
        if is_def:
            return ["action def"]
        st = ["action"]
        tn = getattr(el, "typed_by_name", None)
        if tn:
            st.append(tn.split("::")[-1])
        return st

    def _draw(el, is_def, parent_node=None):
        name = getattr(el, "name", None) or "action"
        nodes[id(el)] = d.add_node(
            name, stereotypes=_stereo(el, is_def),
            attributes=[], rounded=True, parent=parent_node)
        for pname, direction in _params(el, is_def):
            side = "left" if direction == "in" else "right"
            nodes[id(el)].add_port(pname, side=side, label_inside=True)
        return nodes[id(el)]

    # parent lookup for usages (element id -> parent element)
    parent_of = {id(u): p for u, p in usages}

    def _params(el, is_def):
        own = param_names.get(id(el))
        if own:
            return list(own.items())
        de = typed_def.get(id(el))
        if de is not None:
            return list((param_names.get(id(de)) or {}).items())
        return []

    # draw defs that need boxes (with their nested usages)
    for de in defs_to_draw:
        if keep_ids is not None and id(de) not in keep_ids:
            continue
        _draw(de, True)
    for el, parent in usages:
        if keep_ids is not None and id(el) not in keep_ids:
            continue
        pnode = nodes.get(id(parent)) if parent is not None else None
        if id(el) in nodes:
            continue
        _draw(el, False, parent_node=pnode)

    # ---- 5. edges ---------------------------------------------------------
    port_cache = {}

    def _port(node, label, is_source):
        if node is None or not label:
            return None
        key = (id(node), label)
        if key in port_cache:
            return port_cache[key]
        existing = next((p for p in node.ports if p.label == label), None)
        if existing is not None:
            port_cache[key] = existing
            return existing
        side = "right" if is_source else "left"
        same = [p for p in node.ports if p.side == side]
        offset = None
        if len(same) >= 1:
            offset = (len(same) + 1) / 4.0
            if offset > 1.0:
                offset = 0.5
        p = node.add_port(label, side=side, offset=offset, label_inside=True)
        port_cache[key] = p
        return p

    for item in resolved:
        fe, fport, te, tport, label = item[:5]
        dashed = item[5] if len(item) > 5 else False
        if keep_ids is not None and not (
                id(fe) in keep_ids or id(te) in keep_ids):
            continue
        # Under focus, flow partners outside the subtree are still
        # drawn (top-level) so the touching flow has both endpoints.
        for el in (fe, te):
            if id(el) not in nodes:
                _draw(el, bool(getattr(el, "is_definition", False)))
        src = nodes.get(id(fe))
        dst = nodes.get(id(te))
        if src is None or dst is None:
            continue
        sp = _port(src, fport, True)
        tp = _port(dst, tport, False)
        kw = {"label": label}
        if dashed:
            kw["line_style"] = DASHED
        if sp is not None and tp is not None:
            d.add_edge(src, dst, source_port=sp, target_port=tp, **kw)
        else:
            d.add_edge(src, dst, **kw)

    return d


def render_action_flow_view_boxes(
    model: Union[str, "sysmlpy.Model", dict],
    focus: Optional[str] = None,
    routing: str = "orthogonal",
    **layout_kw,
) -> str:
    """Convenience: build + render the boxes action flow view (braille)."""
    d = as_action_flow_view_boxes(model, focus=focus)
    return d.render(routing=routing, **layout_kw)


def render_action_flow_view_boxes_svg(
    model: Union[str, "sysmlpy.Model", dict],
    focus: Optional[str] = None,
    routing: str = "orthogonal",
    scale: float = 1.5,
    **layout_kw,
) -> str:
    """Convenience: build + render the boxes action flow view as SVG."""
    d = as_action_flow_view_boxes(model, focus=focus)
    return d.render_svg(routing=routing, scale=scale, **layout_kw)
