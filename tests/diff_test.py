"""Tests for sysmlpy.diff — semantic model diff (Goal 8)."""

import pytest

import sysmlpy
from sysmlpy import diff_models
from sysmlpy.diff import diff_files, ModelDiff

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
        assert "Fleet::brakes" in added_names
        assert "Fleet::wheels" in removed_names
        assert "Fleet::EngineV2" in added_names
        assert "Fleet::Engine" in removed_names

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
        assert d.summary() == "2 added, 2 removed, 1 changed"

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

    def test_text_identical(self):
        d = diff_models(sysmlpy.loads(OLD), sysmlpy.loads(OLD))
        assert "identical" in d.as_text()

    def test_markdown_sections(self):
        d = diff_models(sysmlpy.loads(OLD), sysmlpy.loads(NEW))
        md = d.as_markdown()
        assert "## Model diff" in md
        assert "### Added" in md
        assert "### Removed" in md
        assert "### Changed" in md
        assert "`Fleet::Vehicle::engine` (PartUsage)" in md
        assert "`typing`: `Engine` → `EngineV2`" in md

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
        assert {c.qualified_name for c in d.added} >= {"Fleet::brakes"}

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