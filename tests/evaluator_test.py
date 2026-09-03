#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the expression evaluator (v0.64.0 — Adoption Roadmap Goal 4).

Covers:
- collect_values: literals, unit values, cross-references, chains
- evaluate_expression: arithmetic, comparison, booleans, functions,
  bindings (what-if), package-level global fallback
- evaluate_calculation: calc def result expressions
- check_constraints: pass/fail/error results and reporting
- CLI: `sysmlpy eval` (--expr / --set / --constraints)
"""

import pytest

from sysmlpy.usage import ureg
from sysmlpy import loads, load_files
from sysmlpy.evaluator import (
    evaluate_expression,
    evaluate_calculation,
    collect_values,
    check_constraints,
    EvaluationError,
    UnknownNameError,
    UnsupportedExpressionError,
    ConstraintReport,
)

MODEL = """package VehicleSpec {
    part def Vehicle {
        attribute mass : Real := 1200;
        attribute speed : Real := 25.0;
        attribute power : Real := mass * speed;
        attribute bigMass : Boolean := mass > 1000;
        part wheels: Wheel[4];
        attribute wheelLoad : Real := mass / 4 [kg];
        constraint c1 { mass > 1000 }
        constraint c2 { mass * speed <= 30000 }
        constraint c3 { mass > 5000 }
        calc def powerTimes2 { mass * speed * 2 }
    }
    part def Wheel {
        attribute radius : Real := 0.3 [m];
    }
}"""


def model():
    return loads(MODEL)


# ---------------------------------------------------------------------------
# collect_values
# ---------------------------------------------------------------------------


class TestCollectValues:

    def test_literals(self):
        vals = collect_values(model())
        assert vals["VehicleSpec::Vehicle::mass"] == 1200
        assert vals["VehicleSpec::Vehicle::speed"] == 25.0
        assert vals["mass"] == 1200  # bare-name alias

    def test_unit_values(self):
        vals = collect_values(model())
        radius = vals["VehicleSpec::Wheel::radius"]
        assert radius == 0.3 * ureg.meter

    def test_derived_values(self):
        vals = collect_values(model())
        assert vals["VehicleSpec::Vehicle::power"] == 30000.0
        assert vals["VehicleSpec::Vehicle::bigMass"] is True

    def test_unit_arithmetic(self):
        vals = collect_values(model())
        load = vals["VehicleSpec::Vehicle::wheelLoad"]
        assert load == 300.0 * ureg.kilogram

    def test_boolean_values(self):
        vals = collect_values(model())
        assert vals["VehicleSpec::Vehicle::bigMass"] is True

    def test_bindings_override(self):
        vals = collect_values(model(), bindings={"mass": 5})
        assert vals["VehicleSpec::Vehicle::mass"] == 5
        assert vals["VehicleSpec::Vehicle::power"] == 125.0

    def test_empty_model(self):
        vals = collect_values(loads("package P { part def V; }"))
        assert vals == {}


# ---------------------------------------------------------------------------
# evaluate_expression
# ---------------------------------------------------------------------------


class TestEvaluateExpression:

    def test_arithmetic(self):
        ev = lambda e: evaluate_expression(
            e, model=model(), element="VehicleSpec::Vehicle"
        )
        assert ev("mass * 2") == 2400
        assert ev("mass / 4") == 300
        assert ev("mass + 100") == 1300
        assert ev("mass - 200") == 1000
        assert ev("mass % 7") == 1200 % 7
        assert ev("2 ** 10") == 1024

    def test_comparison(self):
        ev = lambda e: evaluate_expression(
            e, model=model(), element="VehicleSpec::Vehicle"
        )
        assert ev("mass > 1000") is True
        assert ev("mass == 1200") is True
        assert ev("mass != 1200") is False
        assert ev("speed <= 25.0") is True

    def test_boolean_logic(self):
        ev = lambda e: evaluate_expression(
            e, model=model(), element="VehicleSpec::Vehicle"
        )
        assert ev("mass > 1000 and speed > 20") is True
        assert ev("mass > 1000 or speed > 100") is True
        assert ev("not bigMass") is False

    def test_functions(self):
        ev = lambda e: evaluate_expression(
            e, model=model(), element="VehicleSpec::Vehicle"
        )
        assert ev("sqrt(mass)") == 1200 ** 0.5
        assert ev("abs(-5)") == 5
        assert ev("min(mass, 100)") == 100
        assert ev("max(mass, 5000)") == 5000
        assert ev("floor(speed)") == 25
        assert ev("round(25.4)") == 25

    def test_feature_chain(self):
        v = evaluate_expression(
            "wheels.radius * 2", model=model(),
            element="VehicleSpec::Vehicle",
        )
        assert v == 0.6 * ureg.meter

    def test_bindings(self):
        v = evaluate_expression(
            "mass * speed", model=model(),
            element="VehicleSpec::Vehicle", bindings={"speed": 80},
        )
        assert v == 96000

    def test_unit_bindings(self):
        v = evaluate_expression(
            "mass / 4", model=model(),
            element="VehicleSpec::Vehicle", bindings={"mass": 1200 * ureg.kg},
        )
        assert v == 300 * ureg.kilogram

    def test_global_fallback_without_element(self):
        v = evaluate_expression("mass * speed", model=model())
        assert v == 30000.0

    def test_unknown_name(self):
        with pytest.raises(UnknownNameError):
            evaluate_expression("nonexistent", model=model())

    def test_unknown_function(self):
        with pytest.raises(UnsupportedExpressionError):
            evaluate_expression(
                "frobnicate(mass)", model=model(),
                element="VehicleSpec::Vehicle",
            )

    def test_dimensionality_error(self):
        with pytest.raises(EvaluationError):
            evaluate_expression(
                "mass + speed", model=model(),
                element="VehicleSpec::Vehicle",
                bindings={"mass": 1200 * ureg.kg, "speed": 25.0},
            )

    def test_no_model(self):
        assert evaluate_expression("2 + 3 * 4") == 14
        assert evaluate_expression("sqrt(16)") == 4.0


# ---------------------------------------------------------------------------
# evaluate_calculation
# ---------------------------------------------------------------------------


class TestEvaluateCalculation:

    def test_calc_result(self):
        assert evaluate_calculation(model(), "powerTimes2") == 60000.0

    def test_calc_with_bindings(self):
        v = evaluate_calculation(
            model(), "powerTimes2", bindings={"speed": 10.0}
        )
        assert v == 24000.0

    def test_unknown_calc(self):
        with pytest.raises(UnknownNameError):
            evaluate_calculation(model(), "nope")

    def test_package_level_calc(self):
        m = loads("package P { attribute m : Real := 3; "
                  "calc def twice { m * 2 } }")
        assert evaluate_calculation(m, "twice") == 6


# ---------------------------------------------------------------------------
# check_constraints
# ---------------------------------------------------------------------------


class TestCheckConstraints:

    def test_report_statuses(self):
        report = check_constraints(model())
        assert len(report.results) == 3
        assert len(report.passed) == 2
        assert len(report.failed) == 1
        assert len(report.errored) == 0

    def test_qualified_names(self):
        report = check_constraints(model())
        names = {r.qualified_name for r in report.results}
        assert "VehicleSpec::Vehicle::c1" in names
        assert "VehicleSpec::Vehicle::c3" in names

    def test_expression_text(self):
        report = check_constraints(model())
        r = next(r for r in report.results if r.qualified_name.endswith("c1"))
        assert "mass > 1000" in (r.expression_text or "")

    def test_bindings_flip_result(self):
        report = check_constraints(model(), bindings={"mass": 50})
        # c1 (mass > 1000) and c3 (mass > 5000) now fail; c2 still passes
        assert len(report.failed) == 2
        assert len(report.passed) == 1

    def test_errored_constraint(self):
        m = loads("package P { part def V { attribute a : Real := 1; "
                  "constraint c { a > b } } }")
        report = check_constraints(m)
        assert len(report.errored) == 1
        assert report.errored[0].error

    def test_to_json(self):
        report = check_constraints(model())
        data = report.to_json()
        assert data["summary"]["total"] == 3
        assert data["summary"]["passed"] == 2
        assert data["summary"]["failed"] == 1

    def test_no_constraints(self):
        report = check_constraints(loads("package P { part def V; }"))
        assert report.results == []
        assert report.to_text().startswith("Constraint check: 0")


# ---------------------------------------------------------------------------
# round-trip stability of evaluated models
# ---------------------------------------------------------------------------


class TestModelRoundTrip:

    def test_evaluated_model_still_dumps(self):
        m = model()
        d1 = m.dump()
        collect_values(m)
        check_constraints(m)
        evaluate_calculation(m, "powerTimes2")
        assert m.dump() == d1

    def test_load_files_merge(self, tmp_path):
        f1 = tmp_path / "a.sysml"
        f1.write_text(loads(
            "package P { part def V { attribute m : Real := 2; } }"
        ).dump())
        f2 = tmp_path / "b.sysml"
        f2.write_text(loads(
            "package P { constraint c { m > 1 } }"
        ).dump())
        m = load_files([str(f1), str(f2)])
        report = check_constraints(m)
        assert len(report.passed) == 1


# ---------------------------------------------------------------------------
# CLI: sysmlpy eval
# ---------------------------------------------------------------------------


class TestEvalCommand:
    @pytest.fixture()
    def model_file(self, tmp_path):
        f = tmp_path / "m.sysml"
        f.write_text(loads(MODEL).dump() + "\n")
        return f

    def test_expr(self, model_file, capsys):
        from sysmlpy.__main__ import main
        assert main([
            "eval", str(model_file), "--expr", "mass * 2",
            "--element", "VehicleSpec::Vehicle",
        ]) == 0
        assert capsys.readouterr().out.strip() == "2400"

    def test_expr_with_set(self, model_file, capsys):
        from sysmlpy.__main__ import main
        assert main([
            "eval", str(model_file), "--expr", "mass * speed",
            "--element", "VehicleSpec::Vehicle", "--set", "speed=80",
        ]) == 0
        assert capsys.readouterr().out.strip() == "96000"

    def test_expr_with_unit_set(self, model_file, capsys):
        from sysmlpy.__main__ import main
        assert main([
            "eval", str(model_file), "--expr", "mass / 4",
            "--element", "VehicleSpec::Vehicle", "--set", "mass=1200 kg",
        ]) == 0
        assert "kilogram" in capsys.readouterr().out

    def test_expr_unknown_name_exit_1(self, model_file):
        from sysmlpy.__main__ import main
        assert main([
            "eval", str(model_file), "--expr", "bogus * 2",
        ]) == 1

    def test_constraints_fail_exit_1_by_default(self, model_file, capsys):
        # the fixture's c3 (mass > 5000) fails with mass=1200
        from sysmlpy.__main__ import main
        assert main(["eval", str(model_file), "--constraints"]) == 1
        assert "1 failed" in capsys.readouterr().out

    def test_constraints_fail_exit_1(self, model_file):
        from sysmlpy.__main__ import main
        assert main([
            "eval", str(model_file), "--constraints", "--set", "mass=50",
        ]) == 1

    def test_values_default(self, model_file, capsys):
        from sysmlpy.__main__ import main
        assert main(["eval", str(model_file)]) == 0
        out = capsys.readouterr().out
        assert "mass = 1200" in out

    def test_output_file(self, model_file, tmp_path):
        from sysmlpy.__main__ import main
        out = tmp_path / "report.txt"
        # c2 caps mass*speed at 30000 — satisfy all three together
        assert main([
            "eval", str(model_file), "--constraints", "-o", str(out),
            "--set", "mass=6000", "--set", "speed=0.1",
        ]) == 0
        assert "PASS" in out.read_text(encoding="utf-8")

    def test_missing_file_exit_2(self, tmp_path):
        from sysmlpy.__main__ import main
        assert main(["eval", str(tmp_path / "nope.sysml")]) == 2

    def test_parse_error_exit_2(self, tmp_path):
        f = tmp_path / "broken.sysml"
        f.write_text("package P { part def Broken {")
        from sysmlpy.__main__ import main
        assert main(["eval", str(f), "--constraints"]) == 2

    def test_bad_set_exit_2(self, model_file):
        from sysmlpy.__main__ import main
        assert main([
            "eval", str(model_file), "--expr", "mass", "--set", "nonsense",
        ]) == 2


# ---------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------


class TestPublicApi:
    def test_exports(self):
        import sysmlpy
        assert sysmlpy.evaluate_expression is evaluate_expression
        assert sysmlpy.evaluate_calculation is evaluate_calculation
        assert sysmlpy.collect_values is collect_values
        assert sysmlpy.check_constraints is check_constraints
        assert sysmlpy.ConstraintReport is ConstraintReport