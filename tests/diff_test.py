"""Tests for sysmlpy.diff — semantic model diff (Goal 8)."""

import pytest

import sysmlpy
from sysmlpy import diff_models
from sysmlpy.diff import diff_files, ModelDiff, ElementChange

OLD = """
package Fleet {
    part def Vehicle {
        attribute mass : ScalarValues::Real;
        part engine : Engine;
    }
    abstract part def Engine;
    part v : Vehicle;
    requirement top {
        subject s : Vehicle;
    }
    part wheels;
}
"""

NEW = """
package Fleet {
    part def Vehicle {
        attribute mass : ScalarValues::Real;
        part engine : EngineV2;
    }
    part def EngineV2;
    part v : Vehicle;
    requirement top {
        subject s : Vehicle;
    }
    part brakes;
}
"""


def _codes(d):
    return [c.change for c in d.changes]


class TestDiffModels:
    def test_identical_models_empty(self):
        d = diff_models(sysmlpy.loads(OLD), sysmlpy.loads(OLD))
        assert d.is_empty()
        assert d.added == [] and d.removed == [] and d.changed == []
        assert "identical" in d.summary()

    def test_added_removed_detected(self):
        d = diff_models(sysmlpy.loads(OLD), sysmlpy.loads(NEW))
        added_names = [c.qualified_name for c in d.added]
        removed_names = [c.qualified_name for c in d.removed]
        # wheels -> brakes share kind + structural signature: renamed
        assert "Fleet::EngineV2" in added_names
        assert "Fleet::Engine" in removed_names
        assert {c.old_qualified_name for c in d.renamed} ==             {"Fleet::wheels"}
        assert {c.qualified_name for c in d.renamed} ==             {"Fleet::brakes"}

    def test_typing_change_reported(self):
        d = diff_models(sysmlpy.loads(OLD), sysmlpy.loads(NEW))
        engine = [c for c in d.changed
                  if c.qualified_name == "Fleet::Vehicle::engine"]
        assert len(engine) == 1
        assert engine[0].kind == "PartUsage"
        fields = {fc.field: fc for fc in engine[0].fields}
        assert "typing" in fields
        assert fields["typing"].old == "Engine"
        assert fields["typing"].new == "EngineV2"

    def test_subject_change_reported(self):
        old = sysmlpy.loads(OLD)
        new = sysmlpy.loads(OLD.replace(
            "subject s : Vehicle;", "subject s : Rock;"))
        d = diff_models(old, new)
        top = [c for c in d.changed
               if c.qualified_name == "Fleet::top"]
        assert len(top) == 1
        fields = {fc.field: fc for fc in top[0].fields}
        assert "subject" in fields
        assert "Vehicle" in fields["subject"].old
        assert "Rock" in fields["subject"].new

    def test_kind_change_reports_removed_and_added(self):
        # part def Engine replaced by an inline usage of the same name
        old = sysmlpy.loads("package M { part def Engine; }")
        new = sysmlpy.loads("package M { part Engine; }")
        d = diff_models(old, new)
        kinds = {(c.kind, c.change) for c in d.changes}
        assert ("PartDef", "removed") in kinds
        assert ("PartUsage", "added") in kinds

    def test_model_uuid_excluded(self):
        # Model objects carry a random UUID name per parse — never compare
        d = diff_models(sysmlpy.loads(OLD), sysmlpy.loads(NEW))
        for c in d.changes:
            assert c.kind != "Model"

    def test_summary_counts(self):
        d = diff_models(sysmlpy.loads(OLD), sysmlpy.loads(NEW))
        assert d.summary() == "1 added, 1 removed, 1 renamed, 1 changed"

    def test_sorted_deterministic_order(self):
        d1 = diff_models(sysmlpy.loads(OLD), sysmlpy.loads(NEW))
        d2 = diff_models(sysmlpy.loads(OLD), sysmlpy.loads(NEW))
        assert [(c.kind, c.qualified_name) for c in d1.changes] == \
            [(c.kind, c.qualified_name) for c in d2.changes]


class TestDiffRendering:
    def test_text_markers(self):
        d = diff_models(sysmlpy.loads(OLD), sysmlpy.loads(NEW))
        text = d.as_text()
        assert "+ PartDef  Fleet::EngineV2" in text
        assert "- PartDef  Fleet::Engine" in text
        assert "~ PartUsage  Fleet::Vehicle::engine" in text
        assert "typing: Engine -> EngineV2" in text
        assert "> PartUsage  Fleet::wheels -> Fleet::brakes" in text

    def test_text_identical(self):
        d = diff_models(sysmlpy.loads(OLD), sysmlpy.loads(OLD))
        assert "identical" in d.as_text()

    def test_markdown_sections(self):
        d = diff_models(sysmlpy.loads(OLD), sysmlpy.loads(NEW))
        md = d.as_markdown()
        assert "## Model diff" in md
        assert "### Added" in md
        assert "### Removed" in md
        assert "### Renamed" in md
        assert "### Changed" in md
        assert "`Fleet::Vehicle::engine` (PartUsage)" in md
        assert "`typing`: `Engine` → `EngineV2`" in md
        assert "`Fleet::wheels` → `Fleet::brakes` (PartUsage)" in md

    def test_markdown_identical(self):
        d = diff_models(sysmlpy.loads(OLD), sysmlpy.loads(OLD))
        assert "identical" in d.as_markdown()


class TestDiffFiles:
    def test_diff_files(self, tmp_path):
        old_f = tmp_path / "old.sysml"
        new_f = tmp_path / "new.sysml"
        old_f.write_text(OLD, encoding="utf-8")
        new_f.write_text(NEW, encoding="utf-8")
        d = diff_files(old_f, new_f)
        assert not d.is_empty()
        assert {c.old_qualified_name for c in d.renamed} == {"Fleet::wheels"}
        assert {c.qualified_name for c in d.renamed} == {"Fleet::brakes"}

    def test_diff_files_identical(self, tmp_path):
        f = tmp_path / "m.sysml"
        f.write_text(OLD, encoding="utf-8")
        d = diff_files(f, f)
        assert d.is_empty()

    def test_diff_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            diff_files(tmp_path / "nope.sysml", tmp_path / "nope.sysml")


class TestLazyExports:
    def test_public_exports(self):
        assert sysmlpy.diff_models is diff_models
        assert sysmlpy.diff_files is diff_files
        assert sysmlpy.ModelDiff is ModelDiff


# ---------------------------------------------------------------------------
# v0.82.0 — Batch 3: rename detection, grammar fields, state-machine
# diff, requirement trace edges, change-rate gate
# ---------------------------------------------------------------------------

RENAME_OLD = """
package M {
    part def Engine;
    part power : Engine;
    part chassis;
}
"""

RENAME_NEW = """
package M {
    part def Engine;
    part motor : Engine;
    part drive;
    part drive2;
}
"""

GRAMMAR_OLD = """
package G {
    part def V {
        attribute speed : ScalarValues::Real := 70;
        attribute mode[2] : ScalarValues::Integer;
        attribute batch[1..3] ordered nonunique : ScalarValues::Integer;
        in attribute inp : ScalarValues::Integer := 3;
        doc /* the vehicle */
    }
}
"""

GRAMMAR_VALUE = GRAMMAR_OLD.replace(":= 70", ":= 90")
GRAMMAR_MULT = GRAMMAR_OLD.replace("mode[2]", "mode[3]")
GRAMMAR_DIR = GRAMMAR_OLD.replace("in attribute inp", "out attribute inp")


class TestRenameDetection:
    def test_same_signature_rename_matched(self):
        d = diff_models(sysmlpy.loads(RENAME_OLD),
                        sysmlpy.loads(RENAME_NEW))
        # power -> motor: same kind + typing, unique candidate
        assert [(c.old_qualified_name, c.qualified_name)
                for c in d.renamed] == [("M::power", "M::motor")]
        assert not [c for c in d.changes
                    if c.qualified_name in ("M::power", "M::motor")
                    and c.change != "renamed"]

    def test_rename_carries_field_changes(self):
        old = sysmlpy.loads(
            "package M { requirement a { doc /* one */ } }")
        new = sysmlpy.loads(
            "package M { requirement b { doc /* two */ } }")
        d = diff_models(old, new)
        assert len(d.renamed) == 1
        r = d.renamed[0]
        assert r.old_qualified_name == "M::a"
        assert r.qualified_name == "M::b"
        fields = {fc.field: fc for fc in r.fields}
        assert fields["doc"].old == "one"
        assert fields["doc"].new == "two"

    def test_ambiguous_signature_stays_removed_added(self):
        d = diff_models(sysmlpy.loads(RENAME_OLD),
                        sysmlpy.loads(RENAME_NEW))
        # chassis is untyped like BOTH drive and drive2: ambiguous,
        # so it stays removed + added instead of a rename
        added = {c.qualified_name for c in d.added}
        removed = {c.qualified_name for c in d.removed}
        assert {"M::drive", "M::drive2"} <= added
        assert "M::chassis" in removed
        assert "M::chassis" not in {c.old_qualified_name
                                    for c in d.renamed}

    def test_kind_change_never_matches(self):
        old = sysmlpy.loads("package M { part def Engine; }")
        new = sysmlpy.loads("package M { part Engine; }")
        d = diff_models(old, new)
        assert d.renamed == []
        kinds = {(c.kind, c.change) for c in d.changes}
        assert ("PartDef", "removed") in kinds
        assert ("PartUsage", "added") in kinds

    def test_abstract_flag_blocks_match(self):
        # OLD Fleet::Engine is abstract, EngineV2 is not
        d = diff_models(sysmlpy.loads(OLD), sysmlpy.loads(NEW))
        assert {c.old_qualified_name for c in d.renamed} ==             {"Fleet::wheels"}


class TestGrammarFields:
    def _sig(self, text, name):
        m = sysmlpy.loads(text)
        d = diff_models(m, m)
        return d  # empty; we inspect signatures via a changed pair

    def test_value_change_reported(self):
        d = diff_models(sysmlpy.loads(GRAMMAR_OLD),
                        sysmlpy.loads(GRAMMAR_VALUE))
        changed = [c for c in d.changed
                   if c.qualified_name == "G::V::speed"]
        assert len(changed) == 1
        fields = {fc.field: fc for fc in changed[0].fields}
        assert fields["value"].old == "70"
        assert fields["value"].new == "90"

    def test_multiplicity_change_reported(self):
        d = diff_models(sysmlpy.loads(GRAMMAR_OLD),
                        sysmlpy.loads(GRAMMAR_MULT))
        changed = [c for c in d.changed
                   if c.qualified_name == "G::V::mode"]
        assert len(changed) == 1
        fields = {fc.field: fc for fc in changed[0].fields}
        assert fields["multiplicity"].old == "[2]"
        assert fields["multiplicity"].new == "[3]"

    def test_direction_change_reported(self):
        d = diff_models(sysmlpy.loads(GRAMMAR_OLD),
                        sysmlpy.loads(GRAMMAR_DIR))
        changed = [c for c in d.changed
                   if c.qualified_name == "G::V::inp"]
        assert len(changed) == 1
        fields = {fc.field: fc for fc in changed[0].fields}
        assert fields["direction"].old == "in"
        assert fields["direction"].new == "out"

    def test_doc_change_reported(self):
        # doc is a tree attribute (populated for requirements); usage
        # docs do not survive the grammar round-trip so dumps cannot
        # be mined for them
        old = sysmlpy.loads(
            "package T { requirement r { doc /* the first */ } }")
        new = sysmlpy.loads(
            "package T { requirement r { doc /* the first one */ } }")
        d = diff_models(old, new)
        changed = [c for c in d.changed if c.qualified_name == "T::r"]
        assert len(changed) == 1
        fields = {fc.field: fc for fc in changed[0].fields}
        assert fields["doc"].old == "the first"
        assert fields["doc"].new == "the first one"

    def test_flags_in_multiplicity(self):
        m = sysmlpy.loads(GRAMMAR_OLD)
        from sysmlpy.diff import _dump_fields
        f = m.find_one("batch")
        got = _dump_fields(f)
        assert got["multiplicity"] == "[1..3] ordered nonunique"

    def test_identical_models_still_empty(self):
        d = diff_models(sysmlpy.loads(GRAMMAR_OLD),
                        sysmlpy.loads(GRAMMAR_OLD))
        assert d.is_empty()


TRACE_OLD = """
package T {
    requirement top {
        doc /* the top */
        subject s : Vehicle;
    }
    part def Vehicle;
    part v : Vehicle;
}
"""

TRACE_NEW = TRACE_OLD.replace(
    "part v : Vehicle;", "part v : Vehicle { satisfy top by v; }")


class TestTraceEdges:
    def test_satisfy_edge_change_reported(self):
        d = diff_models(sysmlpy.loads(TRACE_OLD),
                        sysmlpy.loads(TRACE_NEW))
        changed = [c for c in d.changed
                   if c.qualified_name == "T::top"]
        assert len(changed) == 1
        fields = {fc.field: fc for fc in changed[0].fields}
        assert fields["traces"].old is None
        assert "satisfy:v" in fields["traces"].new

    def test_traces_none_without_edges(self):
        m = sysmlpy.loads(TRACE_OLD)
        d = diff_models(m, m)
        assert d.is_empty()

    def test_traces_in_signature(self):
        from sysmlpy.diff import _signature
        from sysmlpy.traceability import extract_traceability
        m = sysmlpy.loads(TRACE_NEW)
        traces = {t.qualified_name: t
                  for t in extract_traceability(m).requirements}
        top = m.find_one("top")
        sig = _signature(top, traces)
        assert sig["traces"] == "satisfy:v"


MACHINE_OLD = """
package S {
    state def Cruise {
        entry; then off;
        state off;
        state engaged;
        transition engage first off accept Engage then engaged;
        transition cancel first engaged accept Cancel then off;
    }
}
"""

MACHINE_NEW = """
package S {
    state def Cruise {
        entry; then off;
        state off;
        state engaged;
        state holding;
        transition engage first off accept Engage when key then engaged;
        transition cancel first engaged accept Cancel then off;
        transition hold first engaged accept SpeedOK then holding;
    }
    attribute key : ScalarValues::Boolean := true;
}
"""


class TestStateMachinDiff:
    def test_states_added_removed(self):
        d = sysmlpy.diff_state_machines(
            sysmlpy.loads(MACHINE_OLD), sysmlpy.loads(MACHINE_NEW))
        added = {c.qualified_name for c in d.added}
        removed = {c.qualified_name for c in d.removed}
        assert "holding" in added
        assert removed == set()

    def test_transition_field_changes(self):
        d = sysmlpy.diff_state_machines(
            sysmlpy.loads(MACHINE_OLD), sysmlpy.loads(MACHINE_NEW))
        changed = [c for c in d.changed
                   if c.kind == "Transition" and c.name == "engage"]
        assert len(changed) == 1
        fields = {fc.field: fc for fc in changed[0].fields}
        assert fields["guard"].old is None
        assert fields["guard"].new == "key"

    def test_transition_added(self):
        d = sysmlpy.diff_state_machines(
            sysmlpy.loads(MACHINE_OLD), sysmlpy.loads(MACHINE_NEW))
        added = {c.qualified_name for c in d.added if c.kind == "Transition"}
        assert "hold" in added

    def test_initial_state_change(self):
        old = MACHINE_OLD.replace("entry; then off;", "entry; then engaged;")
        d = sysmlpy.diff_state_machines(
            sysmlpy.loads(old), sysmlpy.loads(MACHINE_NEW))
        machine = [c for c in d.changed if c.kind == "StateMachine"]
        assert len(machine) == 1
        fields = {fc.field: fc for fc in machine[0].fields}
        assert fields["initial"].old == "engaged"
        assert fields["initial"].new == "off"

    def test_identical_machines_empty(self):
        d = sysmlpy.diff_state_machines(
            sysmlpy.loads(MACHINE_OLD), sysmlpy.loads(MACHINE_OLD))
        assert d.is_empty()

    def test_no_machine_raises(self):
        from sysmlpy.sim import SimulationError
        with pytest.raises(SimulationError):
            sysmlpy.diff_state_machines(
                sysmlpy.loads("package P { part def Q; }"),
                sysmlpy.loads("package P { part def R; }"))

    def test_history_region_in_transition_diff(self):
        old = MACHINE_OLD.replace(
            "transition cancel first engaged accept Cancel then off;",
            "transition cancel first engaged accept Cancel then h; "
            "state h : HistoryUsage;")
        d = sysmlpy.diff_state_machines(
            sysmlpy.loads(old), sysmlpy.loads(MACHINE_OLD))
        # old: cancel targets history (dest = region default entry off)
        changed = [c for c in d.changed if c.kind == "Transition"]
        assert changed == []  # both resolve to the same flat target


class TestChangeRateGate:
    def test_counts_recorded(self):
        d = diff_models(sysmlpy.loads(OLD), sysmlpy.loads(NEW))
        assert d.elements_old > 0
        assert d.elements_new > 0

    def test_change_rate(self):
        d = diff_models(sysmlpy.loads(OLD), sysmlpy.loads(NEW))
        assert 0 < d.change_rate < 1
        d0 = diff_models(sysmlpy.loads(OLD), sysmlpy.loads(OLD))
        assert d0.change_rate == 0.0

    def test_empty_old_rate(self):
        d = ModelDiff(changes=[], elements_old=0)
        assert d.change_rate == 0.0
        d2 = ModelDiff(changes=[ElementChange(
            change="added", kind="PartUsage", name="x",
            qualified_name="M::x")], elements_old=0)
        assert d2.change_rate == 1.0

    def test_lazy_export(self):
        assert sysmlpy.diff_state_machines is sysmlpy.diff.diff_state_machines
