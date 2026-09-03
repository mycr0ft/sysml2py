#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for requirement traceability & verification coverage
(v0.62.0 — Adoption Roadmap Goal 2).

Covers:
- visitor round-trips for verification/satisfy/verify/subject constructs
- requirement trace extraction (satisfy/verify edges, docs, subjects)
- coverage queries and report output (text / markdown / json)
- the traceability matrix view (markdown / html / plantuml)
- the `sysmlpy trace` CLI command
"""

import json
import subprocess
import sys

import pytest

import sysmlpy
from sysmlpy import loads
from sysmlpy.traceability import (
    extract_traceability,
    as_traceability_matrix_view,
    TraceabilityReport,
)


def run_cli(*args):
    """Run the real module entry point in a subprocess."""
    return subprocess.run(
        [sys.executable, "-m", "sysmlpy", *args],
        capture_output=True,
        text=True,
        timeout=600,
    )


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

FULL_MODEL = """package VehicleSpec {
    requirement def MassRequirement {
        doc /* total mass shall not exceed 2000 kg */
        subject : Vehicle;
    }
    requirement totalMass : MassRequirement {
        verify massCheck;
    }
    requirement untracked {
        doc /* nobody satisfies or verifies me */
    }
    part def Vehicle {
        part wheels: Wheel[4];
        attribute mass : Real;
        satisfy totalMass by wheels;
    }
    part def Wheel;
    verification def MassCheck {
        subject : Vehicle;
    }
    verification massCheck : MassCheck;
}"""


def full_model():
    return loads(FULL_MODEL)


# ---------------------------------------------------------------------------
# parse / round-trip of the new constructs
# ---------------------------------------------------------------------------


class TestVerificationRoundTrip:

    def test_verification_def_roundtrip_stable(self):
        m = loads("package P { requirement def R; verification def VDef; }")
        d1 = m.dump()
        assert "verification def VDef" in d1
        assert loads(d1).dump() == d1  # stable re-parse

    def test_verification_def_with_subject(self):
        m = loads(
            "package P { part def Vehicle; verification def VDef "
            "{ subject : Vehicle; } }"
        )
        d1 = m.dump()
        assert "subject : Vehicle" in d1
        assert loads(d1).dump() == d1

    def test_verification_usage_named_and_stable(self):
        m = loads(
            "package P { verification def MassCheck; "
            "verification massCheck : MassCheck; }"
        )
        d1 = m.dump()
        assert "verification massCheck: MassCheck" in d1
        assert loads(d1).dump() == d1
        vc = [
            c for c in m.children[0].children
            if type(c).__name__ == "VerificationCase"
            and type(c.grammar).__name__ == "VerificationCaseUsage"
        ]
        assert len(vc) == 1
        assert vc[0].name == "massCheck"

    def test_verify_member_in_requirement_usage(self):
        m = loads(
            "package P { requirement def R; requirement r1 : R "
            "{ verify v1; } }"
        )
        d1 = m.dump()
        assert "verify v1" in d1
        assert loads(d1).dump() == d1

    def test_verify_inline_declaration(self):
        m = loads(
            "package P { requirement def R; verification def VDef; "
            "requirement r1 : R { verify requirement v2 : VDef; } }"
        )
        d1 = m.dump()
        assert "verify requirement v2" in d1
        assert "VDef" in d1
        assert loads(d1).dump() == d1

    def test_satisfy_roundtrip(self):
        m = loads(
            "package P { requirement r1; part def V { part w; "
            "satisfy r1 by w; } }"
        )
        d1 = m.dump()
        assert "satisfy r1 by w" in d1
        assert loads(d1).dump() == d1


class TestRequirementExtraction:

    def test_subject_anonymous(self):
        m = loads("package P { part def Vehicle; requirement def R "
                  "{ subject : Vehicle; } }")
        req = [c for c in m.children[0].children if c.name == "R"][0]
        assert req.subject == ("Vehicle", "Vehicle")

    def test_subject_named(self):
        m = loads("package P { part def Vehicle; requirement def R "
                  "{ subject v : Vehicle; } }")
        req = [c for c in m.children[0].children if c.name == "R"][0]
        assert req.subject == ("v", "Vehicle")

    def test_verified_by_reference_form(self):
        m = loads("package P { requirement def R; requirement r1 : R "
                  "{ verify v1; } }")
        req = [c for c in m.children[0].children if c.name == "r1"][0]
        assert req.verified_by == ["v1"]

    def test_verified_by_declaration_form(self):
        m = loads("package P { requirement def R; verification def VDef; "
                  "requirement r1 : R { verify requirement v2 : VDef; } }")
        req = [c for c in m.children[0].children if c.name == "r1"][0]
        assert req.verified_by == ["v2"]

    def test_doc_extraction(self):
        m = loads("package P { requirement def R "
                  "{ doc /* the requirement text */ } }")
        req = [c for c in m.children[0].children if c.name == "R"][0]
        assert req.doc == "the requirement text"


# ---------------------------------------------------------------------------
# traceability report
# ---------------------------------------------------------------------------


class TestExtractTraceability:

    def test_finds_all_requirements(self):
        report = extract_traceability(full_model())
        names = [t.name for t in report.requirements]
        assert "MassRequirement" in names
        assert "totalMass" in names
        assert "untracked" in names

    def test_qualified_names(self):
        report = extract_traceability(full_model())
        t = report.by_name("totalMass")
        assert t.qualified_name == "VehicleSpec::totalMass"

    def test_satisfy_edge(self):
        report = extract_traceability(full_model())
        t = report.by_name("totalMass")
        assert t.satisfied_by == ["wheels"]

    def test_verify_edge(self):
        report = extract_traceability(full_model())
        t = report.by_name("totalMass")
        assert t.verified_by == ["massCheck"]

    def test_requirement_text(self):
        report = extract_traceability(full_model())
        t = report.by_name("MassRequirement")
        assert t.text == "total mass shall not exceed 2000 kg"

    def test_subject_in_trace(self):
        report = extract_traceability(full_model())
        t = report.by_name("MassRequirement")
        assert t.subject == ("Vehicle", "Vehicle")

    def test_statuses(self):
        report = extract_traceability(full_model())
        assert report.by_name("totalMass").status == "covered"
        assert report.by_name("untracked").status == "uncovered"

    def test_coverage_summary(self):
        report = extract_traceability(full_model())
        cov = report.coverage()
        assert cov["total"] == 3
        assert cov["covered"] == 1
        assert cov["uncovered"] == 2
        assert abs(cov["coverage_ratio"] - 1 / 3) < 1e-9

    def test_uncovered_unsatisfied_unverified(self):
        report = extract_traceability(full_model())
        unc = [t.name for t in report.uncovered()]
        assert set(unc) == {"MassRequirement", "untracked"}
        unsat = [t.name for t in report.unsatisfied()]
        assert set(unsat) == {"MassRequirement", "untracked"}
        unver = [t.name for t in report.unverified()]
        assert set(unver) == {"MassRequirement", "untracked"}

    def test_forward_reference_creates_trace(self):
        # `satisfy futureReq by w;` where futureReq is declared nowhere
        # still shows up as an edge so the report is complete.
        m = loads("package P { part def V { part w; "
                  "satisfy futureReq by w; } }")
        report = extract_traceability(m)
        t = report.by_name("futureReq")
        assert t is not None
        assert t.satisfied_by == ["w"]

    def test_qualified_satisfy_reference_resolves(self):
        m = loads("package P { requirement totalMass; "
                  "part def V { part w; satisfy P::totalMass by w; } }")
        report = extract_traceability(m)
        t = report.by_name("totalMass")
        assert t.satisfied_by == ["w"]

    def test_partial_status(self):
        m = loads("package P { requirement def R; requirement r1 : R "
                  "{ verify v1; } }")
        report = extract_traceability(m)
        assert report.by_name("r1").status == "partial"

    def test_empty_model_report(self):
        m = loads("package P { part def V; }")
        report = extract_traceability(m)
        assert report.requirements == []
        assert report.coverage()["total"] == 0
        assert report.coverage()["coverage_ratio"] == 0.0


class TestReportOutput:

    def test_to_json_structure(self):
        report = extract_traceability(full_model())
        data = report.to_json()
        assert {"summary", "requirements"} <= set(data)
        assert data["summary"]["total"] == 3
        tm = next(r for r in data["requirements"] if r["name"] == "totalMass")
        assert tm["satisfied_by"] == ["wheels"]
        assert tm["verified_by"] == ["massCheck"]
        assert tm["status"] == "covered"

    def test_to_markdown(self):
        md = extract_traceability(full_model()).to_markdown()
        assert "| Requirement |" in md
        assert "VehicleSpec::totalMass" in md
        assert "wheels" in md
        assert "massCheck" in md
        assert "**Coverage:**" in md

    def test_to_text(self):
        text = extract_traceability(full_model()).to_text()
        assert "3 requirements" in text
        assert "[covered]" in text
        assert "[uncovered]" in text


# ---------------------------------------------------------------------------
# matrix view
# ---------------------------------------------------------------------------


class TestTraceabilityMatrixView:

    def test_markdown_default(self):
        out = as_traceability_matrix_view(full_model())
        assert out.startswith("| Requirement | Status |")
        assert "totalMass" in out

    def test_html(self):
        out = as_traceability_matrix_view(full_model(), output_format="html")
        assert out.startswith("<table")
        assert "totalMass" in out

    def test_plantuml(self):
        out = as_traceability_matrix_view(full_model(), output_format="plantuml")
        assert out.startswith("@startuml")
        assert "..> " in out
        assert ": satisfy" in out
        assert ": verify" in out
        assert out.rstrip().endswith("@enduml")

    def test_focus_filters(self):
        out = as_traceability_matrix_view(
            full_model(), focus="totalMass", output_format="markdown"
        )
        assert "totalMass" in out
        assert "untracked" not in out

    def test_elements_filter(self):
        out = as_traceability_matrix_view(
            full_model(), elements=["wheels"], output_format="markdown"
        )
        assert "totalMass" in out
        assert "untracked" not in out

    def test_show_text(self):
        out = as_traceability_matrix_view(
            full_model(), output_format="markdown", show_text=True
        )
        assert "Text |" in out
        assert "shall not exceed 2000 kg" in out

    def test_style_color(self):
        out = as_traceability_matrix_view(
            full_model(), output_format="plantuml", style="color"
        )
        assert "#dfffdf" in out  # covered
        assert "#ffdfdf" in out  # uncovered

    def test_invalid_format_raises(self):
        m = loads("package P { requirement def R; }")
        with pytest.raises(ValueError):
            as_traceability_matrix_view(m, output_format="svg")


# ---------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------


class TestPublicApi:

    def test_exports(self):
        assert sysmlpy.extract_traceability is extract_traceability
        assert sysmlpy.as_traceability_matrix_view is as_traceability_matrix_view
        assert sysmlpy.TraceabilityReport is TraceabilityReport

    def test_works_with_load_files(self, tmp_path):
        f1 = tmp_path / "req.sysml"
        f1.write_text(loads(
            "package P { requirement r1; part def V; }"
        ).dump())
        f2 = tmp_path / "sat.sysml"
        f2.write_text(loads(
            "package P { part def V { part w; satisfy r1 by w; } }"
        ).dump())
        model = sysmlpy.load_files([str(f1), str(f2)])
        report = extract_traceability(model)
        t = report.by_name("r1")
        assert t is not None
        assert t.satisfied_by == ["w"]


# ---------------------------------------------------------------------------
# CLI: sysmlpy trace
# ---------------------------------------------------------------------------


class TestTraceCommand:

    def test_trace_text_exit_0(self, tmp_path):
        f = tmp_path / "m.sysml"
        f.write_text(loads(FULL_MODEL).dump())
        from sysmlpy.__main__ import main
        assert main(["trace", str(f)]) == 0

    def test_trace_fail_on_uncovered_exit_1(self, tmp_path):
        f = tmp_path / "m.sysml"
        f.write_text(loads(FULL_MODEL).dump())
        from sysmlpy.__main__ import main
        assert main(["trace", str(f), "--fail-on", "uncovered"]) == 1

    def test_trace_fail_on_uncovered_clean_exit_0(self, tmp_path):
        # every requirement covered → exit 0 even with --fail-on uncovered
        f = tmp_path / "m.sysml"
        f.write_text(loads("""package P {
    requirement r1 { verify v1; }
    part def V { part w; satisfy r1 by w; }
    verification def VDef;
    verification v1 : VDef;
}""").dump())
        from sysmlpy.__main__ import main
        assert main(["trace", str(f), "--fail-on", "uncovered"]) == 0

    def test_trace_json(self, tmp_path, capsys):
        f = tmp_path / "m.sysml"
        f.write_text(loads(FULL_MODEL).dump())
        from sysmlpy.__main__ import main
        assert main(["trace", str(f), "--format", "json"]) == 0
        data = json.loads(capsys.readouterr().out)
        assert data["summary"]["total"] == 3
        assert any(r["name"] == "totalMass" for r in data["requirements"])

    def test_trace_markdown(self, tmp_path, capsys):
        f = tmp_path / "m.sysml"
        f.write_text(loads(FULL_MODEL).dump())
        from sysmlpy.__main__ import main
        assert main(["trace", str(f), "--format", "markdown"]) == 0
        assert "| Requirement |" in capsys.readouterr().out

    def test_trace_output_file(self, tmp_path):
        f = tmp_path / "m.sysml"
        f.write_text(loads(FULL_MODEL).dump())
        out = tmp_path / "report.md"
        from sysmlpy.__main__ import main
        assert main(
            ["trace", str(f), "--format", "markdown", "-o", str(out)]
        ) == 0
        content = out.read_text(encoding="utf-8")
        assert "| Requirement |" in content

    def test_trace_missing_file_exit_2(self, tmp_path):
        from sysmlpy.__main__ import main
        assert main(["trace", str(tmp_path / "nope.sysml")]) == 2

    def test_trace_syntax_error_exit_2(self, tmp_path):
        f = tmp_path / "broken.sysml"
        f.write_text("package P { requirement def Broken {")
        from sysmlpy.__main__ import main
        assert main(["trace", str(f)]) == 2

    def test_trace_via_subprocess(self, tmp_path):
        f = tmp_path / "m.sysml"
        f.write_text(loads(FULL_MODEL).dump())
        result = run_cli("trace", str(f), "--format", "json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["summary"]["covered"] == 1