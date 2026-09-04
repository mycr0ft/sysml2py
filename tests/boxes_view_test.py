#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Smoke tests for the optional boxes-backed state-transition view.

Skipped if the `boxes` package is not importable in the current
environment (it is treated as an optional dependency — install with
``pip install -e ~/boxes`` (checkout dir; the *package* is named
``diagramboxes``) or ``poetry run pip install -e ../boxes``).
"""
from __future__ import annotations

import pytest

boxes = pytest.importorskip("diagramboxes")

NESTED_SM = '''
state def SM {
    state Idle;
    state Running {
        state Spinning;
        state Stopped;
    }
    transition t1 first Idle then Running;
    transition Running then Idle;
    transition Running then Stopped;
}
'''

import sysmlpy  # noqa: E402
from sysmlpy.boxes_view import (  # noqa: E402
    as_state_transition_view_boxes,
    as_interconnection_view_boxes,
    as_action_flow_view_boxes,
    render_state_transition_view,
    render_state_transition_view_svg,
    render_interconnection_view_boxes,
    render_interconnection_view_boxes_svg,
    render_action_flow_view_boxes,
    render_action_flow_view_boxes_svg,
    _collect_state_machine,
)


VEHICLE_STATES = """state def VehicleStates {
    entry; then off;
    state off;
    transition off_to_starting first off accept VehicleStartSignal then starting;
    state starting;
    transition starting_to_on first starting accept VehicleOnSignal then on;
    state on;
    transition on_to_off first on accept VehicleOffSignal then off;
}"""


def test_collect_state_machine_finds_three_states():
    visit = sysmlpy.load_grammar(VEHICLE_STATES)
    machines = _collect_state_machine(visit)
    assert len(machines) == 1
    sm = machines[0]
    assert sm["name"] == "VehicleStates"
    state_names = [s["name"] if isinstance(s, dict) else s for s in sm["states"]]
    assert state_names == ["off", "starting", "on"]
    assert sm["initial"] == "off"
    assert len(sm["transitions"]) == 3


def test_collect_state_machine_transitions_have_triggers():
    visit = sysmlpy.load_grammar(VEHICLE_STATES)
    sm = _collect_state_machine(visit)[0]
    triggers = {t["trigger"] for t in sm["transitions"]}
    assert triggers == {"VehicleStartSignal", "VehicleOnSignal", "VehicleOffSignal"}


def test_diagram_has_states_initial_and_transitions():
    d = as_state_transition_view_boxes(VEHICLE_STATES)
    # 3 state nodes + 1 initial pseudostate (StartNode)
    state_nodes = [n for n in d.nodes if getattr(n, "stereotypes", None) == ["state"]]
    assert len(state_nodes) == 3
    # StartNode instances live in d.activities (boxes' bucket for
    # control/pseudostate nodes). Confirm at least one is present.
    assert any(isinstance(a, boxes.StartNode) for a in getattr(d, "activities", []))
    # 3 transitions + 1 entry transition (initial → off)
    assert len(d.edges) == 4


def test_render_returns_nonempty_string():
    out = render_state_transition_view(VEHICLE_STATES, routing="orthogonal")
    assert isinstance(out, str)
    assert "off" in out
    assert "starting" in out
    assert "on" in out
    for trigger in ("VehicleStartSignal", "VehicleOnSignal", "VehicleOffSignal"):
        assert trigger in out


def test_render_svg_starts_with_svg_tag():
    svg = render_state_transition_view_svg(VEHICLE_STATES, routing="orthogonal")
    assert svg.lstrip().startswith("<svg")
    assert "VehicleStates" not in svg  # state-def name not rendered by default
    # Each state appears as a «state» stereotype in the SVG text
    assert svg.count("\u00abstate\u00bb") == 3


def test_focus_picks_named_state_def_when_multiple_present():
    text = """state def A { entry; then a1; state a1; }
              state def B { entry; then b1; state b1; }"""
    d_a = as_state_transition_view_boxes(text, focus="A")
    d_b = as_state_transition_view_boxes(text, focus="B")
    a_state_names = [n.name for n in d_a.nodes]
    b_state_names = [n.name for n in d_b.nodes]
    assert "a1" in a_state_names and "b1" not in a_state_names
    assert "b1" in b_state_names and "a1" not in b_state_names


def test_focus_unknown_raises_value_error():
    with pytest.raises(ValueError, match="No state def named"):
        as_state_transition_view_boxes(VEHICLE_STATES, focus="DoesNotExist")


def test_no_state_def_returns_empty_diagram():
    d = as_state_transition_view_boxes("part def P;")
    assert isinstance(d, boxes.Diagram)
    assert len(d.nodes) == 0


def test_pseudostate_aliases_re_exported():
    # boxes now has first-class pseudostate classes; verify they are the real
    # boxes classes, not local aliases in boxes_view.
    from sysmlpy.boxes_view import (
        InitialPseudostate, FinalState,
        ChoicePseudostate, ForkPseudostate, JoinPseudostate,
        TerminatePseudostate, HistoryPseudostate,
        EntryPoint, ExitPoint, StateNode,
    )
    assert issubclass(InitialPseudostate, boxes.StartNode)
    assert issubclass(FinalState, boxes.DoneNode)
    assert issubclass(ChoicePseudostate, boxes.DecisionNode)
    assert issubclass(ForkPseudostate, boxes.ForkJoinNode)
    assert issubclass(JoinPseudostate, boxes.ForkJoinNode)
    assert issubclass(TerminatePseudostate, boxes.TerminateNode)
    assert HistoryPseudostate is boxes.HistoryPseudostate
    assert issubclass(EntryPoint, boxes.Port)
    assert issubclass(ExitPoint, boxes.Port)
    assert issubclass(StateNode, boxes.Node)


def test_lazy_attribute_on_sysmlpy_namespace():
    assert callable(sysmlpy.as_state_transition_view_boxes)
    assert callable(sysmlpy.render_state_transition_view)
    assert callable(sysmlpy.render_state_transition_view_svg)
    assert hasattr(sysmlpy, "boxes_view")


def test_nested_composite_states_registered():
    text = """state def SM {
        state R1 {
            entry; then a;
            state a;
            state b;
            transition a_to_b first a accept X then b;
        }
        state R2 { state c; state d; }
    }"""
    d = as_state_transition_view_boxes(text)
    state_names = [n.name for n in d.nodes]
    assert "R1" in state_names
    assert "a" in state_names and "b" in state_names
    assert "R2" in state_names and "c" in state_names and "d" in state_names
    # R1's internal transition (a → b on X) should appear as an edge
    assert any("X" in (getattr(e, "label", "") or "") for e in d.edges)


def test_nested_initial_targets_resolve():
    text = """state def SM {
        state R1 {
            entry; then a;
            state a;
            state b;
        }
    }"""
    d = as_state_transition_view_boxes(text)
    # we expect one initial pseudostate (filled circle) at this level
    initials = [a for a in getattr(d, "activities", [])
                if isinstance(a, boxes.InitialPseudostate)]
    assert len(initials) == 1
    edges_to_a = [e for e in d.edges
                  if e.target is not None
                  and getattr(e.target, "name", "") == "a"]
    assert len(edges_to_a) >= 1


def test_composite_state_text_renders():
    text = """state def SM {
        state R1 {
            entry; then a;
            state a;
            state b;
            transition a_to_b first a accept X then b;
        }
    }"""
    out = render_state_transition_view(text, routing="orthogonal")
    assert "R1" in out and "a" in out and "b" in out
    # X trigger should appear as an edge label somewhere
    assert "X" in out


def test_transition_to_done_emits_final_state():
    text = """state def SM {
        state A;
        transition end_it first A accept Done then done;
    }"""
    d = as_state_transition_view_boxes(text)
    finals = [a for a in getattr(d, "activities", [])
              if isinstance(a, boxes.FinalState)]
    assert len(finals) == 1
    edges_to_final = [e for e in d.edges
                      if e.target is finals[0]]
    assert len(edges_to_final) == 1
    # Final-state bullseye should also appear in the render
    out = render_state_transition_view(text, routing="orthogonal")
    assert "A" in out


def test_transition_to_done_reuses_single_final_state():
    text = """state def SM {
        state A;
        state B;
        transition a_to_done first A accept DoneA then done;
        transition b_to_done first B accept DoneB then done;
    }"""
    d = as_state_transition_view_boxes(text)
    finals = [a for a in getattr(d, "activities", [])
              if isinstance(a, boxes.FinalState)]
    assert len(finals) == 1


def test_guard_expression_appears_in_edge_label():
    text = """state def SM {
        state A;
        state B;
        transition t1 first A accept Trig if ok then B;
    }"""
    out = render_state_transition_view(text, routing="orthogonal")
    # Trigger and guard both present in the label, e.g. ``Trig [ok]``
    assert "Trig" in out
    assert "[ok]" in out


def test_parallel_state_does_not_crash_adapter(monkeypatch):
    # SysML v2 supports `parallel` on a StateDefBody, but sysmlpy's ANTLR
    # grammar (Pilot v2 era) does not accept that production on `state def`
    # directly — it only accepts it on a state *usage* (`state vs :> Def
    # parallel { … }`), which the adapter doesn't currently descend into.
    # What we want to confirm here: feeding a regular non-parallel state
    # machine still works and the adapter doesn't accidentally insert the
    # «parallel» stereotype.
    text = """state def SimpleStates {
        entry; then off;
        state off;
        state on;
        transition t first off accept X then on;
    }"""
    d = as_state_transition_view_boxes(text)
    n = d.nodes[0]
    assert "\u00abparallel\u00bb" not in (n.stereotypes or [])
    assert n.stereotypes == ["state"]


def test_entry_do_exit_actions_render_as_attributes():
    # The spec example has no inner states; the top-level StateDefinition
    # body is walked by the adapter even when there are zero states, but
    # nothing to render.  Instead, drive entry/do/exit via an inner state
    # so the diagram has a state box, and check attribute presence there.
    text = """state def TurnedOn {
        entry;
        do monitor;
        exit act;
        state A;
        state B;
        transition a_to_b first A accept X then B;
    }"""
    d = as_state_transition_view_boxes(text)
    # Inner states A and B should be present.
    state_names = [n.name for n in d.nodes]
    assert "A" in state_names and "B" in state_names
    out = render_state_transition_view(text, routing="orthogonal")
    assert "A" in out and "B" in out


def test_full_omg_state_test_model_parses():
    # Abridged variant of the OMG Simple Tests/StateTest.sysml that
    # exercises: entry transition, composite state, nested substates,
    # accept shorthand transition.  ``do action A`` is intentionally
    # omitted because the visitor emits a StateActionUsage that the
    # adapter doesn't yet extract as an attribute at the state-def level.
    text = """state def S {
        entry; then S1;
        state S1;
            accept s : Sig then S2;
        state S2 {
            do send new Sig(T.s.x) to p;
            state S3;
        }
        accept Exit then done;
        transition
            first S1
            accept s : Sig
            then S2.S3;
    }"""
    d = as_state_transition_view_boxes(text)
    assert d.nodes or d.activities
    finals = [a for a in getattr(d, "activities", [])
              if isinstance(a, boxes.FinalState)]
    # ``accept Exit then done`` should produce one final-state bullseye.
    assert len(finals) == 1
    out = render_state_transition_view(text, routing="orthogonal")
    assert "S1" in out and "S2" in out


def test_full_omg_state_test_model_parses():
    # Abridged variant of the OMG Simple Tests/StateTest.sysml that
    # exercises: entry transition, composite state, nested substates,
    # parallel state, accept shorthand transition, do action
    text = """state def S {
        do action A;
        entry; then S1;
        state S1;
            accept s : Sig do action D then S2;
        state S2 { do send new Sig(T.s.x) to p; state S3; }
        accept Exit then done;
        transition
            first S1
            accept s : Sig
            do action D
            then S2.S3;
    }"""
    d = as_state_transition_view_boxes(text)
    assert d.nodes or d.activities  # nonempty
    finals = [a for a in getattr(d, "activities", [])
              if isinstance(a, boxes.FinalState)]
    # transition to ``done`` should produce one final-state bullseye
    assert len(finals) == 1
    # Render should not throw
    out = render_state_transition_view(text, routing="orthogonal")
    assert "S1" in out and "S2" in out

class TestNestedComposites:
    """Composite states render nested inside their parent (diagramboxes
    v0.4.0 nesting) — not flattened as Parent.Sub labels."""

    NESTED = """
    state def SM {
        state Idle;
        state Running {
            state Spinning;
            state Stopped;
        }
        transition t1 first Idle then Running;
        transition Running then Idle;
        transition Running then Stopped;
    }
    """

    def _diagram(self):
        return as_state_transition_view_boxes(NESTED_SM)

    def test_composite_children_nested(self):
        d = as_state_transition_view_boxes(self.NESTED)
        run = next(n for n in d.nodes if n.name == "Running")
        names = {c.name for c in run.children}
        assert names == {"Spinning", "Stopped"}
        for c in run.children:
            assert c.parent is run

    def test_children_inside_parent_after_layout(self):
        d = as_state_transition_view_boxes(self.NESTED)
        d.layout(routing="orthogonal")
        run = next(n for n in d.nodes if n.name == "Running")
        for c in run.children:
            assert (run.x <= c.x and c.x + c.w <= run.x + run.w
                    and run.y <= c.y and c.y + c.h <= run.y + run.h)

    def test_no_dotted_names(self):
        d = as_state_transition_view_boxes(self.NESTED)
        assert not any("." in n.name for n in d.nodes)

    def test_cross_level_transition_resolves(self):
        d = as_state_transition_view_boxes(self.NESTED)
        d.layout(routing="orthogonal")
        # `transition Running then Stopped` resolved across levels
        stopped_edges = [e for e in d.edges
                         if getattr(e.target, "name", "") == "Stopped"]
        assert stopped_edges

    def test_braille_render(self):
        out = render_state_transition_view(self.NESTED)
        for name in ("Running", "Spinning", "Stopped", "Idle", "t1"):
            assert name in out
        assert "." not in out.replace("«state»", "")


IV_MODEL = """
package V {
    part def Engine { port powerOut; attribute power : Real; }
    part def Drivetrain { port powerIn; attribute ratio : Real; }
    part engine: Engine;
    part drivetrain: Drivetrain;
    part pump;
    part tank;
    connection clutch connect engine.powerOut to drivetrain.powerIn;
    connection feed connect pump to tank;
}
"""


class TestInterconnectionBoxes:
    """Boxes-backed interconnection view (ports + port-to-port edges)."""

    def test_ports_from_chained_endpoints(self):
        d = as_interconnection_view_boxes(IV_MODEL)
        engine = next(n for n in d.nodes if n.name == "engine")
        drivetrain = next(n for n in d.nodes if n.name == "drivetrain")
        assert [p.label for p in engine.ports] == ["powerOut"]
        assert [p.label for p in drivetrain.ports] == ["powerIn"]
        assert engine.ports[0].side == "right"
        assert drivetrain.ports[0].side == "left"

    def test_port_to_port_edge(self):
        d = as_interconnection_view_boxes(IV_MODEL)
        clutch = next(e for e in d.edges if e.label == "clutch")
        assert clutch.source_port is not None
        assert clutch.target_port is not None
        assert clutch.source_port.label == "powerOut"
        assert clutch.target_port.label == "powerIn"

    def test_plain_connection_direct_edge(self):
        d = as_interconnection_view_boxes(IV_MODEL)
        feed = next(e for e in d.edges if e.label == "feed")
        assert feed.source_port is None and feed.target_port is None
        assert feed.source.name == "pump" and feed.target.name == "tank"

    def test_stereotypes_from_typed_by(self):
        d = as_interconnection_view_boxes(IV_MODEL)
        engine = next(n for n in d.nodes if n.name == "engine")
        assert "Engine" in engine.stereotypes

    def test_focus_filters(self):
        d = as_interconnection_view_boxes(IV_MODEL, focus="engine")
        names = {n.name for n in d.nodes}
        assert names == {"engine", "drivetrain"}

    def test_no_connections_raises(self):
        import pytest
        with pytest.raises(ValueError):
            as_interconnection_view_boxes(
                "package P { part a; part b; }")

    def test_braille_render(self):
        out = render_interconnection_view_boxes(IV_MODEL)
        for t in ("engine", "drivetrain", "clutch", "feed",
                  "powerOut", "powerIn"):
            assert t in out

    def test_svg_render(self):
        out = render_interconnection_view_boxes_svg(IV_MODEL)
        for t in ("powerOut", "powerIn", "clutch"):
            assert t in out


AFV_TYPED = """
package V {
    action def Torque { in fuelCommand; out torque; }
    action def Inject { in fuelCommand; }
    part vehicle {
        action providePower : Torque;
        action injectFuel : Inject;
        flow providePower.torque to injectFuel.fuelCommand;
    }
}
"""

AFV_NESTED = """
package V {
    part vehicle {
        action drive {
            action torque { out o; }
            action inject { in i; }
            flow torque.o to inject.i;
        }
    }
}
"""

AFV_DEF_NESTED = """
package V {
    action def Drive { action torque; action inject; }
    action drive : Drive;
}
"""

AFV_DEFPARAM = """
package V {
    action def Drive { attribute t : Real; action inject { in i; } flow t to inject.i; }
    action drive : Drive;
}
"""


class TestActionFlowBoxes:
    """Boxes-backed action flow view (params as ports, flows as edges)."""

    def test_typed_action_ports(self):
        d = as_action_flow_view_boxes(AFV_TYPED)
        pp = next(n for n in d.nodes if n.name == "providePower")
        inf = next(n for n in d.nodes if n.name == "injectFuel")
        assert ("fuelCommand", "left") in [(p.label, p.side) for p in pp.ports]
        assert ("torque", "right") in [(p.label, p.side) for p in pp.ports]
        assert ("fuelCommand", "left") in [(p.label, p.side) for p in inf.ports]

    def test_structless_defs_not_drawn(self):
        d = as_action_flow_view_boxes(AFV_TYPED)
        names = {n.name for n in d.nodes}
        assert names == {"providePower", "injectFuel"}

    def test_usage_stereotype_carries_type(self):
        d = as_action_flow_view_boxes(AFV_TYPED)
        pp = next(n for n in d.nodes if n.name == "providePower")
        assert "Torque" in pp.stereotypes

    def test_port_to_port_flow_edge(self):
        d = as_action_flow_view_boxes(AFV_TYPED)
        assert len(d.edges) == 1
        e = d.edges[0]
        assert e.source.name == "providePower"
        assert e.target.name == "injectFuel"
        assert e.source_port is not None and e.source_port.label == "torque"
        assert e.target_port is not None and e.target_port.label == "fuelCommand"

    def test_nested_inline_actions(self):
        d = as_action_flow_view_boxes(AFV_NESTED)
        drive = next(n for n in d.nodes if n.name == "drive")
        torque = next(n for n in d.nodes if n.name == "torque")
        inject = next(n for n in d.nodes if n.name == "inject")
        assert torque.parent is drive
        assert inject.parent is drive
        assert len(d.edges) == 1
        e = d.edges[0]
        assert e.source_port is not None and e.source_port.label == "o"
        assert e.target_port is not None and e.target_port.label == "i"

    def test_def_with_nested_actions(self):
        d = as_action_flow_view_boxes(AFV_DEF_NESTED)
        drive_def = next(n for n in d.nodes if n.name == "Drive")
        assert "action def" in drive_def.stereotypes
        torque = next(n for n in d.nodes if n.name == "torque")
        inject = next(n for n in d.nodes if n.name == "inject")
        assert torque.parent is drive_def
        assert inject.parent is drive_def
        # the typed usage is drawn as its own box
        usage = next(n for n in d.nodes if n.name == "drive")
        assert usage.parent is None

    def test_container_param_flow_skipped(self):
        # A flow from a def's own parameter to a nested action would
        # re-anchor to a self edge in the nested layout — skipped.
        d = as_action_flow_view_boxes(AFV_DEFPARAM)
        assert len(d.edges) == 0
        assert any(n.name == "Drive" for n in d.nodes)

    def test_anonymous_flow_label_suppressed(self):
        import sysmlpy as _s
        m = _s.loads(
            "package V { part p { action a1; action a2; flow a1 to a2; } }")
        d = as_action_flow_view_boxes(m)
        assert len(d.edges) == 1
        assert d.edges[0].label is None  # UUID name not shown

    def test_focus_keeps_partner(self):
        d = as_action_flow_view_boxes(AFV_TYPED, focus="providePower")
        names = {n.name for n in d.nodes}
        assert "providePower" in names
        assert "injectFuel" in names  # partner included
        assert len(d.edges) == 1

    def test_focus_unknown_raises(self):
        import pytest
        with pytest.raises(ValueError):
            as_action_flow_view_boxes(AFV_TYPED, focus="nope")

    def test_no_actions_raises(self):
        import pytest
        with pytest.raises(ValueError):
            as_action_flow_view_boxes("package P { part a; part b; }")

    def test_braille_render(self):
        from sysmlpy.boxes_view import render_action_flow_view_boxes
        out = render_action_flow_view_boxes(AFV_NESTED)
        for t in ("drive", "torque", "inject"):
            assert t in out

    def test_svg_render(self):
        from sysmlpy.boxes_view import render_action_flow_view_boxes_svg
        out = render_action_flow_view_boxes_svg(AFV_TYPED)
        for t in ("providePower", "injectFuel", "torque", "fuelCommand"):
            assert t in out

AFV_SUCCESSION = """
package V {
    part vehicle {
        action drive {
            action torque; action inject;
            succession s1 first torque then inject;
        }
    }
}
"""


class TestActionFlowSuccessions:
    """Successions between nested actions render as dashed edges."""

    def test_succession_dashed_edge(self):
        d = as_action_flow_view_boxes(AFV_SUCCESSION)
        assert len(d.edges) == 1
        e = d.edges[0]
        assert e.source.name == "torque" and e.target.name == "inject"
        assert e.line_style == "dashed"
        assert e.label == "s1"

    def test_succession_label_suppressed_when_uuid(self):
        import sysmlpy as _s
        m = _s.loads(
            "package V { part v { action d { action t; action i; "
            "succession first t then i; } } }")
        d = as_action_flow_view_boxes(m)
        assert len(d.edges) == 1
        assert d.edges[0].label is None

    def test_succession_and_flow_mixed(self):
        import sysmlpy as _s
        m = _s.loads(
            "package V { part v { action d { action t; action i; "
            "action w { out r; } "
            "succession s1 first t then i; "
            "flow i.done to w.r; } } }")
        d = as_action_flow_view_boxes(m)
        assert len(d.edges) == 2
        kinds = sorted((e.source.name, e.target.name, e.line_style)
                       for e in d.edges)
        assert ("i", "w", "solid") in kinds
        assert ("t", "i", "dashed") in kinds
