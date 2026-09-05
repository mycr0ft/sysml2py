#!/usr/bin/env python3
"""Constraint textual bodies — natural-language constraint capture (v0.80.0).

Two mechanisms:

1. *Tagged* bodies — the standard SysML v2 textual representation,
   ``rep language "English" /* ... */``, inside a constraint (or
   calculation) body.  Previously the visitor silently dropped it in
   body context; now it is kept, exposed via
   ``Constraint.body_text`` / ``Constraint.body_language``, and reported
   by ``check_constraints``.

2. *Rescue* — when a constraint body does not parse as SysML/KerML at
   all (e.g. plain English text), the parser salvages it as a textual
   representation (default language ``"English"``) and re-parses, so one
   natural-language constraint no longer fails the whole model load.
   A ``UserWarning`` names every salvaged constraint.

Also regression-covers the constraint *name* fix: ConstraintUsage's
declaration chain is one level deeper than the old name extraction
walked, so parsed constraints appeared in the object tree as anonymous
(``name is None``) and ``find_one`` missed them.
"""

import warnings

import pytest

from sysmlpy import SysMLSyntaxError, check_constraints, loads, load_grammar


BASE = ('package P {{ part def W {{ attribute m : ScalarValues::Real := 1500.0; '
        'constraint {0} {{ {1} }} }} }}')


class TestTaggedRepBody:
    def test_visitor_keeps_textual_representation(self):
        d = load_grammar(BASE.format("c", 'rep language "English" /* x > 0 */'))
        found = []

        def hunt(node):
            if isinstance(node, dict):
                if node.get("name") == "TextualRepresentation":
                    found.append(node)
                for v in node.values():
                    hunt(v)
            elif isinstance(node, list):
                for v in node:
                    hunt(v)
        hunt(d)
        assert len(found) == 1
        assert found[0]["language"] == "English"
        assert "x > 0" in found[0]["body"]

    def test_object_tree_exposes_body(self):
        m = loads(BASE.format("c", 'rep language "English" /* the mass shall be under 2000 kg */'))
        c = m.find_one("c")
        assert c is not None
        assert c.body_text == "the mass shall be under 2000 kg"
        assert c.body_language == "English"
        assert c.textual_representations() == [
            ("English", "the mass shall be under 2000 kg")]

    def test_named_constraint_regression(self):
        """ConstraintUsage names were dropped before the declaration walk."""
        m = loads(BASE.format("c", "m > 0"))
        c = m.find_one("c")
        assert c is not None
        assert c.name == "c"

    def test_round_trip_stable(self):
        m = loads(BASE.format("c", 'rep language "English" /* the mass shall be under 2000 kg */'))
        first = m.dump()
        second = loads(first).dump()
        assert second == first
        assert 'language "English"' in second
        assert "the mass shall be under 2000 kg" in second

    def test_no_warnings_for_valid_models(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            loads(BASE.format("c", "m > 0 and m < 5000"))
        assert not caught


class TestRescue:
    def test_natural_language_body_loads_with_warning(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            m = loads(BASE.format("c", "the mass shall be under 2000 kg"))
        assert len(caught) == 1
        assert "constraint 'c'" in str(caught[0].message)
        assert "textual representation" in str(caught[0].message)
        c = m.find_one("c")
        assert c is not None
        assert c.body_text == "the mass shall be under 2000 kg"
        assert c.body_language == "English"

    def test_valid_siblings_untouched(self):
        src = ('package P { part def W { attribute m : ScalarValues::Real := 100.0; '
               'constraint ok { m > 0 and m < 500 } '
               'constraint bad { mass shall be low } } }')
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            m = loads(src)
        results = {r.qualified_name.rsplit("::", 1)[-1]: r
                   for r in check_constraints(m).results}
        assert results["ok"].passed is True
        assert results["bad"].errored is True
        assert "textual body in language 'English'" in results["bad"].error

    def test_star_slash_body_keeps_original_error(self):
        """A body containing */ cannot be wrapped in a comment; the
        original SysMLSyntaxError must survive."""
        with pytest.raises(SysMLSyntaxError):
            loads('package P { part def W { constraint c { a */ b } } }')

    def test_constraint_def_rescued(self):
        src = 'package P { constraint def Limit { the limit shall be positive } }'
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            m = loads(src)
        assert any("'Limit'" in str(c.message) for c in caught)
        c = m.find_one("Limit")
        assert c is not None
        assert c.body_text == "the limit shall be positive"
        assert c.body_language == "English"

    def test_custom_rescue_language(self):
        src = 'package P { part def W { constraint c { franz soll unter 2000 kg bleiben } } }'
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            m = loads(src, rescue_language="German")
        c = m.find_one("c")
        assert c is not None
        assert c.body_language == "German"
        assert c.body_text == "franz soll unter 2000 kg bleiben"


class TestCheckConstraintsReporting:
    def test_textual_constraint_reported(self):
        m = loads(BASE.format("c", 'rep language "English" /* the mass shall be under 2000 kg */'))
        rep = check_constraints(m)
        assert len(rep.results) == 1
        r = rep.results[0]
        assert r.qualified_name.endswith("::c")
        assert r.expression_text == "the mass shall be under 2000 kg"
        assert r.errored is True
        assert r.passed is False and r.failed is False
        assert "English" in r.error
        assert "not machine-evaluable" in r.error

    def test_expression_constraint_still_evaluates(self):
        m = loads(BASE.format("c", "m > 0 and m < 5000"))
        rep = check_constraints(m)
        assert rep.results[0].passed is True