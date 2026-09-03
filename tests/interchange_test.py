#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the SysML v2 JSON interchange format
(v0.63.0 — Adoption Roadmap Goal 3).

Covers:
- export to JSON-LD-style partition documents (to_interchange)
- import back into live models (from_interchange)
- deterministic identifiers and round-trip stability
- error handling (invalid documents, cycles)
- the `sysmlpy export` / `sysmlpy import` CLI commands
"""

import json
import subprocess
import sys

import pytest

import sysmlpy
from sysmlpy import loads, load_files
from sysmlpy.interchange import (
    to_interchange,
    from_interchange,
    interchange_to_json_text,
)


def run_cli(*args):
    """Run the real module entry point in a subprocess."""
    return subprocess.run(
        [sys.executable, "-m", "sysmlpy", *args],
        capture_output=True,
        text=True,
        timeout=600,
    )


RICH_MODEL = """package VehicleSpec {
    part def Vehicle {
        attribute mass : Real;
        part wheels: Wheel[4];
    }
    part def Wheel;
    requirement def RangeReq {
        doc /* range shall exceed 400 km */
    }
    requirement range : RangeReq {
        verify rangeCheck;
    }
    part myCar : Vehicle {
        satisfy range by wheels;
    }
    verification def RangeCheck;
    verification rangeCheck : RangeCheck;
}"""


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------


class TestExport:

    def test_document_shape(self):
        doc = to_interchange(loads("package P { part def V; }"))
        assert set(doc) >= {"@context", "@id", "@graph"}
        assert isinstance(doc["@graph"], list) and doc["@graph"]
        assert doc["@context"]["@version"] == 1.1

    def test_accepts_sysml_text(self):
        doc = to_interchange("package P { part def V; }")
        types = [e["@type"] for e in doc["@graph"]]
        assert "Package" in types

    def test_every_element_has_id_and_type(self):
        doc = to_interchange(loads("package P { part def V; }"))
        for elem in doc["@graph"]:
            assert "@id" in elem
            assert "@type" in elem

    def test_deterministic_ids(self):
        doc1 = to_interchange(loads("package P { part def V; attribute a: Real; }"))
        doc2 = to_interchange(loads("package P { part def V; attribute a: Real; }"))
        assert doc1 == doc2

    def test_scalars_inline(self):
        doc = to_interchange(loads("package P { part def V; }"))
        pkg = next(e for e in doc["@graph"] if e["@type"] == "Identification"
                   and e.get("declaredName") == "P")
        assert pkg["declaredName"] == "P"
        assert pkg["declaredShortName"] is None  # nulls preserved

    def test_no_dangling_references(self):
        doc = to_interchange(loads(RICH_MODEL))
        ids = {e["@id"] for e in doc["@graph"]}

        def collect_refs(v):
            if isinstance(v, dict):
                if set(v) == {"@id"}:
                    yield v["@id"]
                else:
                    for x in v.values():
                        yield from collect_refs(x)
            elif isinstance(v, list):
                for item in v:
                    yield from collect_refs(item)

        refs = {r for e in doc["@graph"] for r in collect_refs(e)}
        assert refs <= ids, f"dangling refs: {refs - ids}"

    def test_metaclass_types(self):
        doc = to_interchange(loads(RICH_MODEL))
        types = {e["@type"] for e in doc["@graph"]}
        assert "Package" in types
        assert "PartDefinition" in types
        assert "PackageMember" in types
        assert "Documentation" in types
        assert "SatisfyRequirementUsage" in types

    def test_merged_model_from_load_files(self, tmp_path):
        f1 = tmp_path / "a.sysml"
        f1.write_text("package P { part def V; }")
        f2 = tmp_path / "b.sysml"
        f2.write_text("package P { part def W; }")
        model = load_files([str(f1), str(f2)])
        doc = to_interchange(model)  # grammar is None → rebuilt
        types = [e["@type"] for e in doc["@graph"]]
        assert "Package" in types

    def test_empty_model(self):
        model = sysmlpy.Model()
        doc = to_interchange(model)
        assert doc["@graph"]  # root PackageBodyElement present
        root = next(e for e in doc["@graph"] if e["@id"] == doc["@id"])
        assert root["@type"] == "PackageBodyElement"

    def test_invalid_input_type_raises(self):
        with pytest.raises(TypeError):
            to_interchange(42)

    def test_json_text_helper(self):
        doc = to_interchange(loads("package P { part def V; }"))
        text = interchange_to_json_text(doc)
        assert json.loads(text) == doc
        assert "\n" in text  # indented by default


# ---------------------------------------------------------------------------
# import
# ---------------------------------------------------------------------------


class TestImport:

    def test_rich_round_trip(self):
        model = loads(RICH_MODEL)
        rebuilt = from_interchange(to_interchange(model))
        assert rebuilt.dump() == model.dump()

    def test_rebuilt_model_is_queryable(self):
        model = loads(RICH_MODEL)
        rebuilt = from_interchange(to_interchange(model))
        pkg = rebuilt.children[0]
        names = [c.name for c in pkg.children]
        assert "Vehicle" in names
        assert "RangeReq" in names
        assert "myCar" in names

    def test_accepts_json_string(self):
        model = loads("package P { part def V; }")
        j = json.dumps(to_interchange(model))
        rebuilt = from_interchange(j)
        assert rebuilt.dump() == model.dump()

    def test_export_stable_after_import(self):
        model = loads(RICH_MODEL)
        doc = to_interchange(model)
        assert to_interchange(from_interchange(doc)) == doc

    def test_simple_model_round_trip(self):
        text = "package P { attribute a : Real; item i; port p; action act; }"
        model = loads(text)
        rebuilt = from_interchange(to_interchange(model))
        assert rebuilt.dump() == model.dump()

    def test_multiplicity_round_trip(self):
        text = "package P { part def V { part wheels: Wheel[4]; } part def Wheel; }"
        model = loads(text)
        rebuilt = from_interchange(to_interchange(model))
        assert rebuilt.dump() == model.dump()

    def test_traceability_survives_interchange(self):
        # Goal-2 interop: satisfy/verify edges survive a JSON round-trip
        model = loads(RICH_MODEL)
        rebuilt = from_interchange(to_interchange(model))
        report1 = sysmlpy.extract_traceability(model)
        report2 = sysmlpy.extract_traceability(rebuilt)
        assert report1.to_json() == report2.to_json()

    # -- error handling ----------------------------------------------------

    def test_missing_graph_raises(self):
        with pytest.raises(ValueError):
            from_interchange({"foo": 1})

    def test_element_without_id_raises(self):
        with pytest.raises(ValueError):
            from_interchange({"@graph": [{"@type": "Package"}]})

    def test_unknown_reference_raises(self):
        doc = {
            "@id": "root",
            "@graph": [
                {"@id": "a", "@type": "PackageBodyElement",
                 "ownedRelationship": [{"@id": "missing"}]},
            ],
        }
        with pytest.raises(ValueError, match="unknown @id"):
            from_interchange(doc)

    def test_cyclic_reference_raises(self):
        doc = {
            "@id": "a",
            "@graph": [
                {"@id": "a", "@type": "PackageBodyElement",
                 "ownedRelationship": [{"@id": "b"}]},
                {"@id": "b", "@type": "PackageMember",
                 "ownedRelatedElement": {"@id": "b"}},
            ],
        }
        with pytest.raises(ValueError, match="Cyclic"):
            from_interchange(doc)

    def test_invalid_json_string_raises(self):
        with pytest.raises(json.JSONDecodeError):
            from_interchange("{not json")

    def test_non_dict_json_raises(self):
        with pytest.raises(ValueError):
            from_interchange("[1, 2, 3]")

    def test_root_without_relationships_raises(self):
        doc = {
            "@id": "x",
            "@graph": [{"@id": "x", "@type": "Identification"}],
        }
        with pytest.raises(ValueError, match="ownedRelationship"):
            from_interchange(doc)


# ---------------------------------------------------------------------------
# CLI: sysmlpy export / import
# ---------------------------------------------------------------------------


class TestExportCommand:

    def test_export_stdout(self, tmp_path, capsys):
        f = tmp_path / "m.sysml"
        f.write_text(loads(RICH_MODEL).dump())
        from sysmlpy.__main__ import main
        assert main(["export", str(f)]) == 0
        doc = json.loads(capsys.readouterr().out)
        assert "@graph" in doc

    def test_export_output_file(self, tmp_path):
        f = tmp_path / "m.sysml"
        f.write_text(loads(RICH_MODEL).dump())
        out = tmp_path / "m.json"
        from sysmlpy.__main__ import main
        assert main(["export", str(f), "-o", str(out)]) == 0
        doc = json.loads(out.read_text(encoding="utf-8"))
        assert "@graph" in doc

    def test_export_compact(self, tmp_path, capsys):
        f = tmp_path / "m.sysml"
        f.write_text(loads(RICH_MODEL).dump())
        from sysmlpy.__main__ import main
        assert main(["export", str(f), "--compact"]) == 0
        out = capsys.readouterr().out
        assert json.loads(out)["@graph"]
        assert "\n  " not in out  # no indentation

    def test_export_multi_file(self, tmp_path, capsys):
        f1 = tmp_path / "a.sysml"
        f1.write_text("package P { part def V; }")
        f2 = tmp_path / "b.sysml"
        f2.write_text("package P { part def W; }")
        from sysmlpy.__main__ import main
        assert main(["export", str(f1), str(f2)]) == 0
        doc = json.loads(capsys.readouterr().out)
        pkg = next(e for e in doc["@graph"]
                   if e["@type"] == "Identification"
                   and e.get("declaredName") == "P")
        assert pkg

    def test_export_missing_file_exit_2(self, tmp_path):
        from sysmlpy.__main__ import main
        assert main(["export", str(tmp_path / "nope.sysml")]) == 2

    def test_export_parse_error_exit_2(self, tmp_path):
        f = tmp_path / "broken.sysml"
        f.write_text("package P { part def Broken {")
        from sysmlpy.__main__ import main
        assert main(["export", str(f)]) == 2


class TestImportCommand:

    def test_import_stdout_round_trip(self, tmp_path, capsys):
        f = tmp_path / "m.sysml"
        f.write_text(loads(RICH_MODEL).dump())
        out = tmp_path / "m.json"
        from sysmlpy.__main__ import main
        assert main(["export", str(f), "-o", str(out)]) == 0
        capsys.readouterr()
        assert main(["import", str(out)]) == 0
        assert capsys.readouterr().out.strip() == f.read_text().strip()

    def test_import_output_file(self, tmp_path):
        f = tmp_path / "m.sysml"
        f.write_text(loads(RICH_MODEL).dump() + "\n")
        j = tmp_path / "m.json"
        rt = tmp_path / "rt.sysml"
        from sysmlpy.__main__ import main
        assert main(["export", str(f), "-o", str(j)]) == 0
        assert main(["import", str(j), "-o", str(rt)]) == 0
        assert rt.read_text(encoding="utf-8") == f.read_text(encoding="utf-8")

    def test_import_missing_file_exit_2(self, tmp_path):
        from sysmlpy.__main__ import main
        assert main(["import", str(tmp_path / "nope.json")]) == 2

    def test_import_invalid_json_exit_2(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("{not json")
        from sysmlpy.__main__ import main
        assert main(["import", str(f)]) == 2

    def test_import_non_interchange_json_exit_2(self, tmp_path):
        f = tmp_path / "not-interchange.json"
        f.write_text('{"hello": "world"}')
        from sysmlpy.__main__ import main
        assert main(["import", str(f)]) == 2

    def test_subprocess_end_to_end(self, tmp_path):
        f = tmp_path / "m.sysml"
        f.write_text(loads(RICH_MODEL).dump() + "\n")
        j = tmp_path / "m.json"
        rt = tmp_path / "rt.sysml"
        assert run_cli("export", str(f), "-o", str(j)).returncode == 0
        assert run_cli("import", str(j), "-o", str(rt)).returncode == 0
        assert rt.read_text(encoding="utf-8") == f.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------


class TestPublicApi:

    def test_exports(self):
        assert sysmlpy.to_interchange is to_interchange
        assert sysmlpy.from_interchange is from_interchange
        assert sysmlpy.interchange_to_json_text is interchange_to_json_text