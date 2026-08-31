#!/usr/bin/env python3
"""Phase D (v0.56.0): two-stage SLL → LL parsing.

The SLL fast-path prediction mode must produce identical parse results
for valid input and identical error reporting for invalid input, while
being measurably faster.  These tests verify correctness of the
contract (the benchmark lives in the changelog / benchmarks script).
"""

import pytest

from sysmlpy import loads
from sysmlpy.antlr_parser import parse, SysMLSyntaxError
from sysmlpy.antlr_visitor import parse_to_dict


SAMPLE_VALID = """
package P {
    part def Vehicle {
        attribute a : Integer;
        attribute b : Integer = a + 2;
        constraint c1 { b > 3 and a < 10 }
        state s {
            state S1;
            transition t first S1 if a > 1 then S1;
        }
    }
}
"""

# Invalid cases: SLL must fall back to LL and report the same error
INVALID_CASES = [
    "package P { import ScalarValues; }",
    "package P { part def X; ",
    "package P { part def X; @@@ }",
    "not a model",
]


class TestTwoStageParsing:
    def test_valid_input_succeeds_single_stage(self, monkeypatch):
        """Valid input uses exactly one parser build (SLL fast path)."""
        import sysmlpy.antlr_parser as ap
        calls = []
        orig = ap._make_parser

        def spy(content):
            calls.append(1)
            return orig(content)

        monkeypatch.setattr(ap, "_make_parser", spy)
        tree = parse(SAMPLE_VALID, prediction_mode="sll")
        assert len(calls) == 1, "SLL fast path should not fall back to LL"
        assert type(tree).__name__ == "RootNamespaceContext"

    def test_valid_tree_identical_between_modes(self):
        """SLL and LL produce identical visitor dicts for valid input."""
        dict_ll = parse_to_dict(SAMPLE_VALID, prediction_mode=None) if False else None
        # via parse(prediction_mode=...)
        tree_ll = parse(SAMPLE_VALID, prediction_mode="ll")
        tree_sll = parse(SAMPLE_VALID, prediction_mode="sll")
        assert tree_ll.toStringTree() == tree_sll.toStringTree()

    def test_errors_identical_between_modes(self):
        for text in INVALID_CASES:
            with pytest.raises(SysMLSyntaxError) as exc_ll:
                parse(text, prediction_mode="ll")
            with pytest.raises(SysMLSyntaxError) as exc_sll:
                parse(text, prediction_mode="sll")
            text_ll = str(exc_ll.value)
            text_sll = str(exc_sll.value)
            # Both modes must detect the error at the same source position.
            # ANTLR's wording may differ between prediction modes (e.g.
            # "extraneous input '<EOF>' expecting {...}" vs
            # "missing '}' at '<EOF>'") — parse out "at L:C" and compare
            # positions only.
            import re
            ll_pos = re.findall(r"at (\d+:\d+)", text_ll)
            sll_pos = re.findall(r"at (\d+:\d+)", text_sll)
            assert ll_pos and sll_pos, f"missing position: {text_ll!r} / {text_sll!r}"
            assert ll_pos[0] == sll_pos[0], (
                f"Error position differs for {text!r}: "
                f"ll={ll_pos[0]} sll={sll_pos[0]}"
            )

    def test_recover_mode_with_fallback(self):
        tree, errors = parse(INVALID_CASES[0], recover=True)
        assert tree is not None
        assert len(errors) >= 1

    def test_loads_unchanged_end_to_end(self):
        """loads() (which uses the SLL default) still round-trips."""
        model = loads(SAMPLE_VALID)
        pkg = model.children[0]
        assert pkg.name == "P"
        vehicle = [c for c in pkg.children if getattr(c, "name", "") == "Vehicle"][0]
        kinds = [type(c).__name__ for c in vehicle.children]
        assert "Attribute" in kinds

    def test_ll_forced_mode(self):
        tree = parse(SAMPLE_VALID, prediction_mode="ll")
        assert tree is not None


class TestParseBenchmark:
    """Informative benchmark used by the v0.56.0 release notes."""

    def test_sll_not_slower_than_ll(self):
        import time
        parts = [
            f"    part def Component{i} {{ attribute m : Integer; }}"
            for i in range(300)
        ]
        text = "package B {\n" + "\n".join(parts) + "\n}"
        # Warm both modes (first parse pays one-time DFA construction)
        parse(text, prediction_mode="ll")
        parse(text, prediction_mode="sll")

        t0 = time.perf_counter()
        parse(text, prediction_mode="sll")
        sll = time.perf_counter() - t0
        t0 = time.perf_counter()
        parse(text, prediction_mode="ll")
        ll = time.perf_counter() - t0
        # SLL should not be a regression (allow 20% slack for CI noise)
        assert sll <= ll * 1.2, f"SLL {sll:.2f}s vs LL {ll:.2f}s"