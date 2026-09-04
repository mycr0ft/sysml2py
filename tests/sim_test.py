#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""State-machine simulation tests (Cameo-style MVP, sysmlpy.sim).

Covers: machine extraction (states/initial/transitions incl. shorthand
guards), guarded firing against evaluated model values, run-to-completion,
effect *logging* (the visitor currently drops ``do <ref>`` on
transitions — see TODO), TUI drive, and value overrides.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest

import sysmlpy
from sysmlpy import boxes_view
from sysmlpy.sim import (
    SimulationError,
    StateSimulator,
    build_state_machine,
    run_tui,
)

CRUISE = """
package Sim {
    attribute speed : ScalarValues::Real := 30;
    attribute key : ScalarValues::Boolean := true;

    action def logState;
    action def hold;

    state def Cruise {
        entry; then off;
        state off;
        state engaged;
        state holding;
        state slowing;
        transition engage first off accept Engage when key do logState then engaged;
        transition hold first engaged accept SpeedOK do hold then holding;
        transition slow first holding accept Decel when speed > 40 do logState then slowing;
        transition resume first slowing accept SpeedOK then holding;
        transition stop first holding accept Off when speed <= 5 then off;
        transition cancel first engaged accept Cancel then off;
    }
}
"""


def _sim(text=CRUISE, **kwargs):
    return StateSimulator(sysmlpy.loads(text), **kwargs)


class TestExtraction:
    def test_flat_machine_states_and_initial(self):
        md = build_state_machine(sysmlpy.loads(CRUISE))
        assert md.name == "Cruise"
        assert md.initial == "off"
        assert md.states == ["off", "engaged", "holding", "slowing"]
        assert md.notes == []

    def test_triggers_guards_effects_resolved(self):
        md = build_state_machine(sysmlpy.loads(CRUISE))
        by_name = {t.name: t for t in md.transitions}
        assert by_name["engage"].trigger == "Engage"
        assert by_name["engage"].guard == "key"
        assert by_name["slow"].guard == "speed > 40"
        assert by_name["resume"].trigger == "SpeedOK"
        assert by_name["resume"].guard is None
        # effects resolve from parsed models (``do <ref>`` rides the
        # visitor's EffectBehaviorMember.ownedRelatedElement)
        assert by_name["engage"].effect == "logState"
        assert by_name["hold"].effect == "hold"
        assert by_name["slow"].effect == "logState"
        assert by_name["resume"].effect is None
        assert by_name["stop"].effect is None
        assert by_name["cancel"].effect is None

    def test_completion_transition_has_no_trigger(self):
        model = sysmlpy.loads("""
        package M {
            state def Machine {
                entry; then a;
                state a;
                state b;
                transition done first a then b;
                transition reset first b accept Kick then a;
            }
        }
        """)
        md = build_state_machine(model)
        triggers = {t.name: t.trigger for t in md.transitions}
        assert triggers["reset"] == "Kick"
        assert triggers["done"] is None

    def test_unknown_focus_raises(self):
        with pytest.raises(SimulationError,
                           match="(?i)no state machine named"):
            build_state_machine(sysmlpy.loads(CRUISE), focus="Nope")

    def test_no_machine_raises(self):
        with pytest.raises(SimulationError, match="contains no state"):
            build_state_machine(sysmlpy.loads("package P { part def Q; }"))

    def test_parallel_machine_raises(self, monkeypatch):
        # The ANTLR grammar does not yet take the textual ``parallel``
        # keyword (boxes-view precedent), so feed a synthetic parallel
        # descriptor to pin the guard.
        def _fake_collect(visit):
            return [{"name": "P", "parallel": True, "states": ["a"],
                     "initial": "a", "transitions": [], "composites": []}]

        monkeypatch.setattr(boxes_view, "_collect_state_machine",
                            _fake_collect)
        with pytest.raises(SimulationError, match="(?i)parallel"):
            build_state_machine(sysmlpy.loads("package P { part def Q; }"))


class TestFiring:
    def test_initial_state_from_entry_transition(self):
        assert _sim().state == "off"

    def test_send_fires_when_guard_true(self):
        sim = _sim()
        assert sim.send("Engage") is True  # key := true in the model
        assert sim.state == "engaged"

    def test_send_blocked_when_guard_false(self):
        sim = _sim()
        sim.set_value("key", False)
        assert sim.send("Engage") is False
        assert sim.state == "off"
        blocked = sim.log[-1]
        assert blocked.fired is False
        assert blocked.guard == "key"
        assert blocked.guard_ok is False

    def test_send_unknown_trigger(self):
        sim = _sim()
        assert sim.send("Nope") is False
        assert sim.state == "off"
        assert "not a trigger from 'off'" in sim.log[-1].note

    def test_trigger_guard_fallthrough(self):
        """Same trigger from one state with different guards: the
        first guard that holds fires (Cameo-style)."""
        sim = _sim("""
        package F {
            attribute speed : ScalarValues::Real := 70;
            state def M {
                entry; then s;
                state s;
                state fast;
                state slow;
                transition down first s accept Decel when speed > 40 then fast;
                transition crawl first s accept Decel when speed <= 40 then slow;
            }
        }
        """)
        assert sim.send("Decel") is True
        assert sim.state == "fast"
        sim.set_value("speed", 10)
        sim.reset()
        assert sim.send("Decel") is True
        assert sim.state == "slow"

    def test_guard_evaluated_against_model_values(self):
        sim = _sim()
        sim.send("Engage")           # key := true
        sim.send("SpeedOK")          # -> holding
        # speed := 30 in the model: Off (speed <= 5) must NOT fire
        assert sim.send("Off") is False
        sim.set_value("speed", 5)
        assert sim.send("Off") is True
        assert sim.state == "off"

    def test_step_prefers_completion_transition(self):
        sim = _sim("""
        package M {
            state def Machine {
                entry; then a;
                state a;
                state b;
                transition auto first a then b;
                transition by_signal first a accept Go then b;
            }
        }
        """)
        assert sim.step() is True
        assert sim.state == "b"

    def test_step_uses_guarded_signal_when_no_completion(self):
        sim = _sim()
        sim.set_value("key", False)
        assert sim.step() is False  # guard false, nothing fires
        sim.set_value("key", True)
        assert sim.step() is True
        assert sim.state == "engaged"

    def test_reset_returns_to_initial(self):
        sim = _sim()
        sim.send("Engage")
        assert sim.state == "engaged"
        sim.reset()
        assert sim.state == "off"
        assert sim.log == []


class TestInspection:
    def test_available_lists_trigger_guard_status(self):
        sim = _sim()
        sim.set_value("key", True)
        avail = sim.available()
        triggers = [a[0] for a in avail]
        assert triggers == ["Engage"]
        assert avail[0][1] == "key"
        assert avail[0][2] is True

    def test_available_shows_false_guard(self):
        sim = _sim()
        sim.set_value("key", False)
        assert sim.available()[0][2] is False

    def test_available_includes_completion_transitions(self):
        sim = _sim("""
        package M {
            state def Machine {
                entry; then a;
                state a;
                state b;
                transition auto first a then b;
            }
        }
        """)
        assert sim.available() == [(None, None, None)]

    def test_set_value_changes_guard_results(self):
        sim = _sim()
        sim.send("Engage")
        sim.send("SpeedOK")          # -> holding
        assert sim.available() == [("Decel", "speed > 40", False),
                                   ("Off", "speed <= 5", False)]
        sim.set_value("speed", 70)
        avail = sim.available()
        assert (avail[0][0], avail[0][2]) == ("Decel", True)
        assert (avail[1][0], avail[1][2]) == ("Off", False)


class TestLogging:
    def test_fired_transition_logged(self):
        sim = _sim()
        sim.send("Engage")
        rec = sim.log[-1]
        assert rec.fired is True
        assert rec.from_state == "off"
        assert rec.trigger == "Engage"
        assert rec.guard == "key"
        assert rec.guard_ok is True
        assert rec.to_state == "engaged"

    def test_effect_logged_when_present(self):
        sim = _sim()
        sim.send("Engage")           # do logState
        assert sim.log[-1].effects == ["logState"]

    def test_effect_send_form_surfaces_as_text(self):
        sim = _sim("""
        package M {
            part def logger;
            state def Machine {
                entry; then a;
                state a;
                state b;
                transition go first a accept Go do send Alert to logger then b;
                transition back first b accept Kick then a;
            }
        }
        """)
        md = sim.descriptor
        effects = {t.name: t.effect for t in md.transitions}
        assert effects["go"] == "send Alert to logger"
        sim.send("Go")
        assert sim.log[-1].effects == ["send Alert to logger"]

    def test_effect_assignment_rendered(self):
        sim = _sim("""
        package M {
            attribute x : ScalarValues::Integer := 0;
            state def Machine {
                entry; then a;
                state a;
                state b;
                transition set1 first a accept Set do x := 5 then b;
                transition back first b accept Kick then a;
            }
        }
        """)
        effects = {t.name: t.effect for t in sim.descriptor.transitions}
        assert effects["set1"] == "x := 5"
        sim.send("Set")
        assert sim.log[-1].effects == ["x := 5"]

    def test_no_effect_logged_when_none(self):
        sim = _sim("""
        package M {
            state def Machine {
                entry; then a;
                state a;
                state b;
                transition go first a accept Kick then b;
            }
        }
        """)
        sim.send("Kick")
        assert sim.log[-1].effects == []


class TestCompositeFlattening:
    def test_flat_machine_has_no_implicit_states(self):
        model = sysmlpy.loads("""
        package M {
            state def VehicleStates {
                entry; then off;
                state off;
                transition off_to_starting first off accept StartSignal then starting;
                state starting;
                transition starting_to_on first starting accept OnSignal then on;
                state on;
                transition on_to_off first on accept OffSignal then off;
            }
        }
        """)
        md = build_state_machine(model)
        assert md.states == ["off", "starting", "on"]
        assert all("implicitly" not in n for n in md.notes)

    def test_transition_into_substate_adds_it_flat(self):
        model = sysmlpy.loads("""
        package M {
            state def Machine {
                entry; then a;
                state a;
                state b {
                    state inner;
                }
                transition go first a accept Go then inner;
            }
        }
        """)
        md = build_state_machine(model)
        assert "inner" in md.states
        sim = StateSimulator(model)
        assert sim.send("Go") is True
        assert sim.state == "inner"


class TestCompositeRegions:
    """Composite states expand flat with qualified names: entering a
    composite lands in its initial substate, its region runs its own
    transitions, and transitions declared on the composite apply from
    every substate (UML composite transitions)."""

    MODEL = """
    package M {
        attribute key : ScalarValues::Boolean := true;
        state def Machine {
            entry; then a;
            state a;
            transition go first a accept Go then b;
            transition stop first b accept Stop then a;

            state b {
                entry; then warmup;
                state warmup;
                state running;
                transition spin first warmup accept Spun then running;
                transition halt first running accept Halt then warmup;
            }
        }
    }
    """

    def test_expansion_and_entry_point(self):
        md = build_state_machine(sysmlpy.loads(self.MODEL))
        assert md.states == ["a", "b.warmup", "b.running"]
        # 'go' targets the composite -> enters its initial substate
        go = next(t for t in md.transitions if t.name == "go")
        assert go.target == "b.warmup"
        # the note fires when the machine's *initial* state is the
        # composite; a retargeting transition stays silent

    def test_region_transitions_run_inside(self):
        sim = StateSimulator(sysmlpy.loads(self.MODEL))
        assert sim.send("Go") is True
        assert sim.state == "b.warmup"        # entry point
        assert sim.send("Spun") is True
        assert sim.state == "b.running"       # region-internal
        assert sim.send("Halt") is True
        assert sim.state == "b.warmup"

    def test_composite_transition_applies_from_any_substate(self):
        sim = StateSimulator(sysmlpy.loads(self.MODEL))
        sim.send("Go")
        assert sim.send("Stop") is True       # from b.warmup
        assert sim.state == "a"
        sim.send("Go")
        assert sim.send("Spun") is True       # now in b.running
        assert sim.send("Stop") is True       # still exits
        assert sim.state == "a"

    def test_nested_composites_qualify(self):
        model = sysmlpy.loads("""
        package M {
            state def Machine {
                entry; then outer;
                state outer {
                    entry; then o1;
                    state o1;
                    transition dive first o1 accept Dive then deep;
                    state deep {
                        entry; then d1;
                        state d1;
                    }
                }
            }
        }
        """)
        sim = StateSimulator(model)
        assert sim.state == "outer.o1"
        assert sim.send("Dive") is True
        assert sim.state == "outer.deep.d1"

    def test_initial_composite_enters_substate(self):
        model = sysmlpy.loads("""
        package M {
            state def Machine {
                entry; then comp;
                state comp {
                    entry; then c1;
                    state c1;
                    state c2;
                    transition flip first c1 accept Flip then c2;
                }
            }
        }
        """)
        md = build_state_machine(model)
        assert md.initial == "comp.c1"
        assert ("entering composite 'comp' at its initial substate "
                "'comp.c1'") in md.notes
        sim = StateSimulator(model)
        assert sim.state == "comp.c1"
        assert sim.send("Flip") is True
        assert sim.state == "comp.c2"

    def test_parallel_region_inside_composite_raises(self, monkeypatch):
        # The textual ``parallel`` keyword is not parseable yet (grammar
        # gap, see boxes-view tests) — feed a synthetic composite whose
        # region declares parallel.
        def _fake_collect(visit):
            return [{"name": "M", "parallel": False,
                     "states": [
                         {"name": "a"},
                         {"name": "comp", "parallel": True,
                          "states": ["p1", "p2"], "initial": "p1",
                          "transitions": [], "composites": []},
                     ],
                     "initial": "a",
                     "transitions": [], "composites": []}]

        monkeypatch.setattr(boxes_view, "_collect_state_machine",
                            _fake_collect)
        with pytest.raises(SimulationError, match="(?i)parallel"):
            StateSimulator(sysmlpy.loads("package P { part def Q; }"))


class TestTUI:
    def test_headless_drive_via_input_func(self):
        lines = iter(["set key=true", "Engage", "q"])
        out = []
        result = run_tui(sysmlpy.loads(CRUISE),
                         input_func=lambda _p="": next(lines),
                         output=out.append)
        assert result.state == "engaged"
        joined = "\n".join(o for o in out if isinstance(o, str))
        assert "current: 'engaged'" in joined

    def test_headless_eof_snapshot(self):
        out = []
        sim = run_tui(sysmlpy.loads(CRUISE),
                      input_func=lambda _p="": None,
                      output=out.append)
        assert sim is not None
        assert sim.state == "off"

    def test_run_tui_reports_simulation_error(self):
        out = []
        result = run_tui(sysmlpy.loads("package P { part def Q; }"),
                         input_func=lambda _p="": None,
                         output=out.append)
        assert result is None
        assert any("contains no state" in o for o in out)


class TestValues:
    def test_values_seed_overrides_model_defaults(self):
        sim = _sim(values={"speed": 70})
        sim.send("Engage")
        sim.send("SpeedOK")  # -> holding
        # Off (speed <= 5) still false, but Decel (speed > 40) now true:
        assert sim.send("Decel") is True

    def test_set_value_updates(self):
        sim = _sim()
        sim.set_value("speed", 70)
        assert sim.values["speed"] == 70


class TestParseValue:
    def test_bool_int_float_str(self):
        from sysmlpy.sim import _parse_value

        assert _parse_value("true") is True
        assert _parse_value("false") is False
        assert _parse_value("5") == 5
        assert _parse_value("70.5") == 70.5
        assert _parse_value(" engaged ") == "engaged"