#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the sysmlpy command line interface (v0.61.0 — Adoption
Roadmap Goal 1: analyze + view commands with CI-friendly exit codes).

Exit code contract (documented in the CLI help):
    0  success / clean analysis
    1  findings at or above the --fail-on threshold (analyze), an
       operational error (view) or a would-reformat check (format --check)
    2  parse/load failure or usage error

The legacy flat invocation (``sysmlpy FILE --dump``) keeps its original
behavior: exit 1 on file/parse errors.
"""

import json
import subprocess
import sys

import pytest

from sysmlpy import loads
from sysmlpy.__main__ import main


# ---------------------------------------------------------------------------
# fixtures / helpers
# ---------------------------------------------------------------------------

CLEAN_TEXT = """package P {
    part def Vehicle {
        part wheels: Wheel[4];
    }
    part def Wheel;
}
"""

BAD_REF_TEXT = """package P {
    part def Vehicle {
        part x :> UndefinedFeature;
    }
}
"""

SYNTAX_ERROR_TEXT = """package P {
    part def Broken {
"""

SYNTAX_ERROR_TEXT = """package P {
    part def Broken {
"""

# Bare library type reference triggers IMPLICIT_LIBRARY_IMPORT (warning).
WARNING_TEXT = """package P {
    part def Hub {
        attribute mass: Real;
    }
}
"""

# Rich model for view smoke tests. as_sequence_view (sv) is exercised on a
# minimal model instead — it has a pre-existing bug with state bodies.
RICH_TEXT = """package P {
    part def Vehicle {
        part wheels: Wheel[4];
        port p1: P1;
        action drive;
    }
    part def Wheel;
    port def P1;
    action def Drive;
    state def Mode {
        state off;
        state on;
        transition off_to_on
            first off
            accept VehicleStartSignal
            then on;
    }
    calc def Speed {
        return attribute v: ScalarValues::Real;
    }
}
"""

MINIMAL_TEXT = """package P {
    part def Vehicle {
        part wheels: Wheel[4];
    }
    part def Wheel;
}
"""


def _write(tmp_path, name, text=CLEAN_TEXT, canonical=True):
    """Write a SysML file; canonicalize so `format --check` passes."""
    if canonical:
        text = loads(text).dump()
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def run_cli(*args):
    """Run the real module entry point in a subprocess."""
    return subprocess.run(
        [sys.executable, "-m", "sysmlpy", *args],
        capture_output=True,
        text=True,
        timeout=600,
    )


# ---------------------------------------------------------------------------
# analyze
# ---------------------------------------------------------------------------


class TestAnalyzeCommand:

    def test_analyze_clean_exit_0(self, tmp_path):
        f = _write(tmp_path, "clean.sysml")
        assert main(["analyze", str(f)]) == 0

    def test_analyze_undefined_symbol_exit_1(self, tmp_path, capsys):
        f = _write(tmp_path, "bad.sysml", BAD_REF_TEXT)
        assert main(["analyze", str(f)]) == 1
        out = capsys.readouterr().out
        assert "UNDEFINED_SYMBOL" in out
        assert "error:" in out

    def test_analyze_syntax_error_exit_2(self, tmp_path, capsys):
        f = tmp_path / "broken.sysml"
        f.write_text(SYNTAX_ERROR_TEXT)
        assert main(["analyze", str(f)]) == 2
        assert "Parse error" in capsys.readouterr().err

    def test_analyze_multiple_files_merged(self, tmp_path):
        f1 = _write(tmp_path, "p1.sysml", """package P {
    part def Vehicle {
        part wheels: Wheel[4];
    }
}""")
        f2 = _write(tmp_path, "p2.sysml", """package P {
    part def Wheel;
}""")
        # Separate files each flag the cross-file reference as undefined;
        # merged they resolve. The CLI must load them as one model.
        assert main(["analyze", str(f1), str(f2)]) == 0

    def test_analyze_json_structure(self, tmp_path, capsys):
        f = _write(tmp_path, "bad.sysml", BAD_REF_TEXT)
        assert main(["analyze", str(f), "--format", "json"]) == 1
        data = json.loads(capsys.readouterr().out)
        assert data["files"] == [str(f)]
        assert data["summary"]["errors"] >= 1
        assert any(i["code"] == "UNDEFINED_SYMBOL" for i in data["issues"])
        assert all(
            {"severity", "code", "message"} <= set(i) for i in data["issues"]
        )

    def test_analyze_json_clean(self, tmp_path, capsys):
        f = _write(tmp_path, "clean.sysml")
        assert main(["analyze", str(f), "--format", "json"]) == 0
        data = json.loads(capsys.readouterr().out)
        assert data["summary"] == {"errors": 0, "warnings": 0}

    def test_analyze_missing_file_exit_2(self, tmp_path, capsys):
        rc = main(["analyze", str(tmp_path / "nope.sysml")])
        assert rc == 2
        assert "not found" in capsys.readouterr().err

    def test_analyze_warning_default_exit_0(self, tmp_path, capsys):
        f = _write(tmp_path, "warn.sysml", WARNING_TEXT)
        assert main(["analyze", str(f)]) == 0
        out = capsys.readouterr().out
        assert "IMPLICIT_LIBRARY_IMPORT" in out
        assert "warning:" in out

    def test_analyze_fail_on_warning_exit_1(self, tmp_path):
        f = _write(tmp_path, "warn.sysml", WARNING_TEXT)
        assert main(["analyze", str(f), "--fail-on", "warning"]) == 1

    def test_analyze_fail_on_never_exit_0(self, tmp_path):
        f = _write(tmp_path, "bad.sysml", BAD_REF_TEXT)
        assert main(["analyze", str(f), "--fail-on", "never"]) == 0

    def test_analyze_no_warnings_flag(self, tmp_path, capsys):
        f = _write(tmp_path, "warn.sysml", WARNING_TEXT)
        assert main(["analyze", str(f), "--no-warnings"]) == 0
        out = capsys.readouterr().out
        assert "IMPLICIT_LIBRARY_IMPORT" not in out


# ---------------------------------------------------------------------------
# view
# ---------------------------------------------------------------------------


class TestViewCommand:

    def test_view_all_views_smoke(self, tmp_path, capsys):
        f = _write(tmp_path, "rich.sysml", RICH_TEXT)
        for name in ("gv", "pv", "afv", "iv", "stv", "cv", "tabular",
                     "datavalue", "matrix", "browser"):
            assert main(["view", str(f), "--view", name]) == 0
        # sv (sequence view) has a pre-existing bug with state bodies; use
        # a state-free model for it.
        f2 = _write(tmp_path, "minimal.sysml", MINIMAL_TEXT)
        assert main(["view", str(f2), "--view", "sv"]) == 0

    def test_view_tabular_markdown(self, tmp_path, capsys):
        f = _write(tmp_path, "clean.sysml")
        assert main(
            ["view", str(f), "--view", "tabular", "--format", "markdown"]
        ) == 0
        out = capsys.readouterr().out
        assert "| Name |" in out

    def test_view_tabular_html(self, tmp_path, capsys):
        f = _write(tmp_path, "clean.sysml")
        rc = main(
            ["view", str(f), "--view", "tabular", "--format", "html"]
        )
        assert rc == 0
        assert "<table" in capsys.readouterr().out

    def test_view_gv_plantuml(self, tmp_path, capsys):
        f = _write(tmp_path, "clean.sysml")
        assert main(["view", str(f), "--view", "gv"]) == 0
        out = capsys.readouterr().out
        assert out.startswith("@startuml")

    def test_view_output_to_file(self, tmp_path, capsys):
        f = _write(tmp_path, "clean.sysml")
        out_file = tmp_path / "gv.puml"
        assert main(["view", str(f), "--view", "gv", "-o", str(out_file)]) == 0
        assert out_file.read_text(encoding="utf-8").startswith("@startuml")
        assert "Wrote" in capsys.readouterr().out

    def test_view_unknown_focus_exit_1(self, tmp_path, capsys):
        f = _write(tmp_path, "clean.sysml")
        rc = main(["view", str(f), "--view", "gv", "--focus", "NoSuch"])
        assert rc == 1
        assert "no element with that name" in capsys.readouterr().err

    def test_view_ambiguous_focus_exit_1(self, tmp_path, capsys):
        # Two parts named 'x' in different namespaces make find_one raise.
        f = _write(tmp_path, "ambig.sysml", """package P {
    part def A { part x; }
    part def B { part x; }
}""")
        rc = main(["view", str(f), "--view", "gv", "--focus", "x"])
        assert rc == 1

    def test_view_unknown_name_rejected(self, tmp_path):
        f = _write(tmp_path, "clean.sysml")
        with pytest.raises(SystemExit):
            main(["view", str(f), "--view", "bogus"])

    def test_view_parse_error_exit_2(self, tmp_path, capsys):
        f = tmp_path / "broken.sysml"
        f.write_text(SYNTAX_ERROR_TEXT)
        assert main(["view", str(f), "--view", "gv"]) == 2

    def test_view_graceful_failure_on_view_bug(self, tmp_path, capsys):
        # as_sequence_view currently crashes on models with state bodies;
        # the CLI must report the failure instead of tracebacking.
        f = _write(tmp_path, "rich.sysml", RICH_TEXT)
        rc = main(["view", str(f), "--view", "sv"])
        assert rc == 1
        assert "failed on this model" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# parse
# ---------------------------------------------------------------------------


class TestParseCommand:

    def test_parse_dump(self, tmp_path, capsys):
        f = _write(tmp_path, "clean.sysml")
        assert main(["parse", str(f), "--dump"]) == 0
        assert "part def Vehicle" in capsys.readouterr().out

    def test_parse_json(self, tmp_path, capsys):
        f = _write(tmp_path, "clean.sysml")
        assert main(["parse", str(f), "--json"]) == 0
        data = json.loads(capsys.readouterr().out)
        assert "ownedRelationship" in data

    def test_parse_default_repr(self, tmp_path, capsys):
        f = _write(tmp_path, "clean.sysml")
        assert main(["parse", str(f)]) == 0
        assert "Model" in capsys.readouterr().out

    def test_parse_missing_file(self, tmp_path, capsys):
        rc = main(["parse", str(tmp_path / "nope.sysml")])
        assert rc == 2


# ---------------------------------------------------------------------------
# format
# ---------------------------------------------------------------------------


class TestFormatCommand:

    def test_format_check_canonical_exit_0(self, tmp_path):
        f = _write(tmp_path, "clean.sysml")  # written canonicalized
        assert main(["format", str(f), "--check"]) == 0

    def test_format_check_noncanonical_exit_1(self, tmp_path, capsys):
        f = tmp_path / "noncanonical.sysml"
        f.write_text("package P { part def A; }")
        assert main(["format", str(f), "--check"]) == 1
        assert "would be reformatted" in capsys.readouterr().out

    def test_format_in_place(self, tmp_path):
        f = tmp_path / "noncanonical.sysml"
        f.write_text("package P { part def A; }")
        assert main(["format", str(f), "-i"]) == 0
        assert loads(f.read_text(encoding="utf-8")).dump() == (
            f.read_text(encoding="utf-8")
        )

    def test_format_stdout(self, tmp_path, capsys):
        f = tmp_path / "noncanonical.sysml"
        f.write_text("package P { part def A; }")
        assert main(["format", str(f)]) == 0
        assert "part def A" in capsys.readouterr().out

    def test_format_multiple_files(self, tmp_path):
        f1 = _write(tmp_path, "a.sysml")
        f2 = _write(tmp_path, "b.sysml", MINIMAL_TEXT)
        assert main(["format", str(f1), str(f2), "--check"]) == 0


# ---------------------------------------------------------------------------
# legacy flat invocation (backward compatibility)
# ---------------------------------------------------------------------------


class TestLegacyInvocation:

    def test_legacy_dump(self, tmp_path, capsys):
        f = _write(tmp_path, "clean.sysml")
        assert main([str(f), "--dump"]) == 0
        assert "part def Vehicle" in capsys.readouterr().out

    def test_legacy_json(self, tmp_path, capsys):
        f = _write(tmp_path, "clean.sysml")
        assert main([str(f), "--json"]) == 0
        json.loads(capsys.readouterr().out)

    def test_legacy_check_exit_0(self, tmp_path):
        f = _write(tmp_path, "clean.sysml")
        assert main([str(f), "--check"]) == 0

    def test_legacy_check_noncanonical_exit_1(self, tmp_path):
        f = tmp_path / "noncanonical.sysml"
        f.write_text("package P { part def A; }")
        assert main([str(f), "--check"]) == 1

    def test_legacy_missing_file_returns_1(self, tmp_path):
        # Legacy behavior preserved: exit code 1 (not the subcommands' 2).
        # The console script wrapper (sys.exit(main())) keeps the same
        # observable process exit code.
        assert main([str(tmp_path / "nope.sysml")]) == 1

    def test_legacy_parse_error_returns_1(self, tmp_path):
        f = tmp_path / "broken.sysml"
        f.write_text(SYNTAX_ERROR_TEXT)
        assert main([str(f)]) == 1


# ---------------------------------------------------------------------------
# module entry point (subprocess)
# ---------------------------------------------------------------------------


class TestModuleEntryPoint:

    def test_version_flag(self):
        result = run_cli("--version")
        assert result.returncode == 0
        assert "sysmlpy" in result.stdout

    def test_analyze_via_module(self, tmp_path):
        f = _write(tmp_path, "clean.sysml")
        result = run_cli("analyze", str(f))
        assert result.returncode == 0

    def test_analyze_findings_exit_code_via_module(self, tmp_path):
        f = tmp_path / "bad.sysml"
        f.write_text(BAD_REF_TEXT)
        result = run_cli("analyze", str(f))
        assert result.returncode == 1
        assert "UNDEFINED_SYMBOL" in result.stdout