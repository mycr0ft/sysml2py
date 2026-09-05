#!/usr/bin/env python3
"""Reference parsing — `ref` usages now appear in the object tree (v0.79.1).

Before this fix, `ref` members were silently dropped at two levels:
- package-level `ref r : Engine;` — the visitor's package-member
  dispatch (`_visit_usage_element_dict`) had no referenceUsage branch;
- nested `ref driver : Person;` inside part bodies — the grammar kept
  them, but the public-API class dispatch never built Reference
  children.

Also covers the `Reference.__init__` fix: it must initialize the full
base-Usage state (freshly built objects crashed `repr()` /
`is_definition` with AttributeError on `_is_definition`).
"""

import pytest

from sysmlpy import Reference, loads


class TestPackageLevelRef:
    def test_ref_in_object_tree(self):
        model = loads("package P { part def Engine; ref r : Engine; }")
        r = model.find_one("r")
        assert r is not None
        assert r.__class__.__name__ == "Reference"
        assert r.sysml_type == "reference"

    def test_ref_typed_by_name(self):
        model = loads("package P { part def Engine; ref r : Engine; }")
        r = model.find_one("r")
        assert r.typed_by_name == "Engine"

    def test_ref_round_trip(self):
        model = loads("package P { part def Engine; ref r : Engine; }")
        assert model.dump() == (
            "package P {\n   part def Engine;\n    ref r: Engine;\n}"
        )

    def test_ref_resolve_types_links(self):
        model = loads("package P { part def Engine; ref r : Engine; }")
        assert model.resolve_types() == 1
        r = model.find_one("r")
        engine = model.find_one("Engine")
        assert r.ref_type is engine
        assert r.typedby is engine

    def test_visibility_prefixed_ref(self):
        model = loads("package P { part def E; private ref r : E; }")
        assert model.find_one("r") is not None
        assert "ref r: E;" in model.dump()


class TestNestedRef:
    def test_nested_ref_in_part_body(self):
        model = loads(
            "package P { part def Person; part car { ref driver : Person; } }"
        )
        car = model.find_one("car")
        driver = model.find_one("driver")
        assert driver is not None
        assert driver.__class__.__name__ == "Reference"
        assert driver.parent is car
        assert driver in car.children

    def test_nested_ref_round_trip(self):
        model = loads(
            "package P { part def Person; part car { ref driver : Person; } }"
        )
        assert model.dump() == (
            "package P {\n   part def Person;\n"
            "   part car {\n       ref driver: Person;\n   }\n}"
        )


class TestRedefinedRef:
    def test_redefined_ref_name_from_redefinition(self):
        """`ref :>> payload : Fuel;` has null declaredName in the grammar;
        the public object's name comes from the redefinition."""
        model = loads(
            "package P { part def Fuel; part tank { ref :>> payload : Fuel; } }"
        )
        payload = model.find_one("payload")
        assert payload is not None
        assert payload.redefines is True
        assert payload.typed_by_name == "Fuel"

    def test_redefined_ref_round_trip(self):
        model = loads(
            "package P { part def Fuel; part tank { ref :>> payload : Fuel; } }"
        )
        assert model.dump() == (
            "package P {\n   part def Fuel;\n   part tank {\n"
            "       ref :>> payload : Fuel;\n   }\n}"
        )


class TestReferenceInit:
    def test_fresh_reference_repr(self):
        """Regression: Reference.__init__ must initialize the base-Usage
        state — repr()/is_definition used to crash with AttributeError."""
        r = Reference(name="driver")
        assert repr(r).startswith("Reference(name='driver')")
        assert r.is_definition is False

    def test_fresh_reference_container_protocol(self):
        r = Reference(name="x")
        assert len(r) == 0  # no children
        assert r.name == "x"

    def test_programmatic_dump_unchanged(self):
        """The v0.78.0 documented programmatic forms still hold."""
        person = Reference(name="Person")  # standalone, no type
        assert person.dump() == "ref Person;"

        item = loads("package P { item def Person; }").find_one("Person")
        r = Reference(name="driver")
        r.set_type(item)
        assert r.dump() == "ref driver : Person;"