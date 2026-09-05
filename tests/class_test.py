#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jul 11 16:46:28 2023

@author: mycr0ft
"""

import pytest
import pint

from sysmlpy.formatting import classtree
from sysmlpy import Package, Item, Model, Attribute, Part, Port, Requirement
from sysmlpy import load_grammar as loads
from sysmlpy.usage import ureg
from .functions import strip_ws


def test_package():
    p = classtree(Package()._get_definition()).dump()

    text = """package ;"""
    q = classtree(loads(text)).dump()

    assert p == q


def test_package_name():
    name = "Rocket"
    p = classtree(Package()._set_name(name)._get_definition()).dump()

    text = "package " + name + ";"
    q = classtree(loads(text)).dump()

    assert p == q


def test_package_shortname():
    name = "'3.1'"
    p = classtree(Package()._set_name(name, short=True)._get_definition()).dump()

    text = "package <" + name + ">;"
    q = classtree(loads(text)).dump()

    assert p == q


def test_package_setbothnames():
    name = "Rocket"
    shortname = "'3.1'"
    p = classtree(
        Package()._set_name(name)._set_name(shortname, short=True)._get_definition()
    ).dump()

    text = "package <" + shortname + "> " + name + ";"
    q = classtree(loads(text)).dump()

    assert p == q


def test_package_getname():
    name = "Rocket"
    p = Package()._set_name(name)
    assert p._get_name() == name


def test_package_addchild():
    p1 = Package()._set_name("Rocket")
    p2 = Package()._set_name("Engine")
    p1._set_child(p2)
    p = classtree(p1._get_definition()).dump()

    text = """package Rocket {
       package Engine;
    }"""

    q = classtree(loads(text)).dump()

    assert p == q


def test_package_get_child():
    p1 = Package()._set_name("Rocket")
    p2 = Package()._set_name("Engine")
    p1._set_child(p2)
    p = classtree(p1._get_child("Rocket.Engine")._get_definition()).dump()

    text = """package Engine;"""

    q = classtree(loads(text)).dump()

    assert p == q


def test_package_get_child_method2():
    p1 = Package()._set_name("Rocket")
    p2 = Package()._set_name("Engine")
    p1._set_child(p2)
    p = classtree(p1._get_child("Engine")._get_definition()).dump()

    text = """package Engine;"""

    q = classtree(loads(text)).dump()

    assert p == q


def test_package_typed_child():
    p1 = Package()._set_name("Rocket")
    i1 = Item(definition=True)._set_name("Fuel")
    i2 = Item()._set_name("Hydrogen")
    p1._set_child(i2)
    i2._set_typed_by(i1)
    p = classtree(p1._get_definition()).dump()

    text = """package Rocket {
       item def Fuel ;
       item Hydrogen : Fuel;
    }"""

    q = classtree(loads(text)).dump()

    assert p == q


def test_package_load_grammar():
    p = Package()

    text = """package Rocket {
       item def Fuel ;
       item Hydrogen : Fuel;
    }"""
    q = Model().load(text)
    p.load_from_grammar(q._get_child("Rocket")._get_grammar())

    assert p.dump() == q.dump()


def test_model_cannot_dump_error():
    m = Model()
    with pytest.raises(ValueError, match="Base Model has no elements."):
        m.dump()


def test_model_load_error_not_package_def():
    text = """item def Fuel ;"""
    with pytest.raises(
        ValueError, match="Base Model must be encapsulated by a package."
    ):
        Model().load(text)


def test_model_load_error_not_package_usage():
    text = """item Fuel ;"""
    with pytest.raises(
        ValueError, match="Base Model must be encapsulated by a package."
    ):
        Model().load(text)


def test_model_add_child():
    m = Model()
    p1 = Package()._set_name("Rocket")
    p2 = Package()._set_name("Payload")
    m._set_child(p1)
    m._set_child(p2)

    text = """package Rocket; 
    package Payload;"""
    q = classtree(loads(text))
    assert m.dump() == q.dump()


def test_model_get_child():
    m = Model()
    p1 = Package()._set_name("Rocket")
    p2 = Package()._set_name("Payload")
    m._set_child(p1)
    m._set_child(p2)
    m2 = m._get_child("Rocket")

    text = """package Rocket;"""
    q = classtree(loads(text))
    assert m2.dump() == q.dump()


def test_model_load():
    p1 = Package()._set_name("Rocket")
    i1 = Item(definition=True)._set_name("Fuel")
    i2 = Item()._set_name("Hydrogen")
    p1._set_child(i2)
    i2._set_typed_by(i1)
    p = classtree(p1._get_definition())

    text = """package Rocket {
       item def Fuel ;
       item Hydrogen : Fuel;
    }"""

    q = Model().load(text)

    assert p.dump() == q.dump()


def test_item():
    i1 = Item()
    text = """item;"""
    i2 = classtree(loads(text))

    assert i1.dump() == i2.dump()


def test_item_def():
    i1 = Item(definition=True)
    text = """item def;"""
    i2 = classtree(loads(text))

    assert i1.dump() == i2.dump()


def test_item_name():
    i1 = Item()._set_name("Fuel")
    text = """item Fuel;"""
    i2 = classtree(loads(text))

    assert i1.dump() == i2.dump()


def test_item_shortname():
    i1 = Item()._set_name("'3.1'", short=True)
    text = """item <'3.1'>;"""
    i2 = classtree(loads(text))

    assert i1.dump() == i2.dump()


def test_item_getname():
    name = "Fuel"
    i1 = Item()._set_name(name)

    assert i1._get_name() == name


def test_item_setchild():
    i1 = Item()._set_name("Fuel")
    ic1 = Item()
    i1._set_child(ic1)
    text = """item Fuel {
        item;
    }"""
    i2 = classtree(loads(text))

    assert i1.dump() == i2.dump()


def test_item_getchild():
    i1 = Item()._set_name("Fuel")
    ic1 = Item()._set_name("Fuel_child")
    i1._set_child(ic1)
    text = """item Fuel_child;"""
    i2 = classtree(loads(text))

    assert i1._get_child("Fuel.Fuel_child").dump() == i2.dump()


def test_item_getchild_skipelement():
    i1 = Item()._set_name("Fuel")
    ic1 = Item()._set_name("Fuel_child")
    i1._set_child(ic1)
    text = """item Fuel_child;"""
    i2 = classtree(loads(text))

    assert i1._get_child("Fuel_child").dump() == i2.dump()


def test_item_getchild_threelevel():
    i1 = Item()._set_name("Fuel")
    ic1 = Item()._set_name("child")
    ic2 = Item()._set_name("subchild")
    i1._set_child(ic1)
    ic1._set_child(ic2)
    text = """item subchild;"""
    i2 = classtree(loads(text))

    assert i1._get_child("Fuel.child.subchild").dump() == i2.dump()


def test_item_getchild_error_int():
    i1 = Item()._set_name("Fuel")
    ic1 = Item()._set_name("Fuel_child")
    i1._set_child(ic1)
    with pytest.raises(TypeError):
        i1._get_child(1)


def test_item_getchild_error_str():
    i1 = Item()._set_name("Fuel")
    ic1 = Item()._set_name("Fuel_child")
    i1._set_child(ic1)
    assert i1._get_child("Fuel.error") == None


def test_item_typedby():
    p1 = Package()._set_name("Store")
    i1 = Item()._set_name("apple")
    i2 = Item(definition=True)._set_name("Fruit")
    p1._set_child(i1)
    i1._set_typed_by(i2)

    text = """package Store {
       item def Fruit ;
       item apple : Fruit;
    }"""
    p2 = classtree(loads(text))

    assert p1.dump() == p2.dump()


def test_item_typedby_invalidusage_twousage():
    i1 = Item()._set_name("apple")
    i2 = Item()._set_name("Fruit")
    with pytest.raises(ValueError):
        i1._set_typed_by(i2)


def test_item_typedby_invalidusage_twodef():
    i1 = Item(definition=True)._set_name("apple")
    i2 = Item(definition=True)._set_name("Fruit")
    with pytest.raises(ValueError):
        i1._set_typed_by(i2)


def test_part_load_grammar():
    p = Part()

    text = """package Rocket {
        package EngineAssembly;
        part Tank {
            item def Fuel ;
            item Hydrogen : Fuel;
        }
    }"""
    q = Model().load(text)._get_child("Rocket.Tank")
    p.load_from_grammar(q._get_grammar())

    assert p.dump() == q.dump()


def test_part():
    i1 = Part()
    text = """part;"""
    i2 = classtree(loads(text))

    assert i1.dump() == i2.dump()


def test_part_def():
    i1 = Part(definition=True)
    text = """part def;"""
    i2 = classtree(loads(text))

    assert i1.dump() == i2.dump()


def test_part_name():
    i1 = Part()._set_name("Fuel")
    text = """part Fuel;"""
    i2 = classtree(loads(text))

    assert i1.dump() == i2.dump()


def test_part_shortname():
    i1 = Part()._set_name("'3.1'", short=True)
    text = """part <'3.1'>;"""
    i2 = classtree(loads(text))

    assert i1.dump() == i2.dump()


def test_part_getname():
    name = "Fuel"
    i1 = Part()._set_name(name)

    assert i1._get_name() == name


def test_part_setchild():
    i1 = Part()._set_name("Fuel")
    ic1 = Part()
    i1._set_child(ic1)
    text = """part Fuel {
        part;
    }"""
    i2 = classtree(loads(text))

    assert i1.dump() == i2.dump()


def test_part_getchild():
    i1 = Part()._set_name("Fuel")
    ic1 = Part()._set_name("Fuel_child")
    i1._set_child(ic1)
    text = """part Fuel_child;"""
    i2 = classtree(loads(text))

    assert i1._get_child("Fuel.Fuel_child").dump() == i2.dump()


def test_part_getchild_error_int():
    i1 = Part()._set_name("Fuel")
    ic1 = Part()._set_name("Fuel_child")
    i1._set_child(ic1)
    with pytest.raises(TypeError):
        i1._get_child(1)


def test_part_getchild_error_str():
    i1 = Part()._set_name("Fuel")
    ic1 = Part()._set_name("Fuel_child")
    i1._set_child(ic1)
    assert i1._get_child("Fuel.error") == None


def test_part_typedby():
    p1 = Package()._set_name("Store")
    i1 = Part()._set_name("apple")
    i2 = Part(definition=True)._set_name("Fruit")
    p1._set_child(i1)
    i1._set_typed_by(i2)

    text = """package Store {
       part def Fruit ;
       part apple : Fruit;
    }"""
    p2 = classtree(loads(text))

    assert p1.dump() == p2.dump()


def test_part_typedby_invalidusage_twousage():
    i1 = Part()._set_name("apple")
    i2 = Part()._set_name("Fruit")
    with pytest.raises(ValueError):
        i1._set_typed_by(i2)


def test_part_typedby_invalidusage_twodef():
    i1 = Part(definition=True)._set_name("apple")
    i2 = Part(definition=True)._set_name("Fruit")
    with pytest.raises(ValueError):
        i1._set_typed_by(i2)


def test_port():
    o1 = Port()
    text = """port;"""
    o2 = classtree(loads(text))

    assert o1.dump() == o2.dump()


def test_port_def():
    o1 = Port(definition=True)
    text = """port def;"""
    o2 = classtree(loads(text))

    assert o1.dump() == o2.dump()


def test_port_directed_in():
    o1 = Port()._set_name("FuelHose")
    o1.add_directed_feature("in", "Fuel")
    text = """port FuelHose {
       in Fuel ;
    }"""
    o2 = classtree(loads(text))
    assert o1.dump() == o2.dump()


def test_port_directed_out():
    o1 = Port()._set_name("FuelHose")
    o1.add_directed_feature("out", "Fuel")
    text = """port FuelHose {
       out Fuel ;
    }"""
    o2 = classtree(loads(text))
    assert o1.dump() == o2.dump()


def test_port_directed_inout():
    o1 = Port()._set_name("FuelHose")
    o1.add_directed_feature("inout", "Fuel")
    text = """port FuelHose {
       inout Fuel ;
    }"""
    o2 = classtree(loads(text))
    assert o1.dump() == o2.dump()


def test_port_directed_error():
    o1 = Port()
    with pytest.raises(ValueError):
        o1.add_directed_feature("error", "Fuel")


def test_item_def_subchild():
    """Item definition with nested attribute should survive round-trip."""
    text = """item Engine {
        attribute mass= 100.0 [kg];
    }"""
    q = classtree(loads(text)).dump()
    assert "attribute mass" in q
    assert "100.0" in q


def test_nested_definition_with_mixed_children():
    """PartDefinition with mixed definition+usage children should survive round-trip.

    Regression test: definition types (PartDefinition, ItemDefinition, etc.)
    were silently dropped when mixed with usage types in the same body.
    """
    import sysmlpy
    text = """package P {
        part def Vehicle {
            part def Engine;
            attribute mass : Real;
        }
    }"""
    m = sysmlpy.loads(text)
    out = m.dump()
    assert "part def Engine" in out
    assert "attribute mass" in out
    assert "Vehicle" in out


def test_deeply_nested_definition():
    """Deeply nested part definitions should survive round-trip.

    Regression test for the exact scenario from the sysml-style bug report.
    """
    import sysmlpy
    text = """package Test {
        public import OMGIDL::*;
        part Module : IDLModule {
            attribute :>> identifier = "Module";
            part def NestedType :> IDLStruct {
                part field1 : IDLField {
                    attribute :>> identifier = "field1";
                }
            }
        }
    }"""
    m = sysmlpy.loads(text)
    out = m.dump()
    assert "NestedType" in out
    assert "field1" in out
    assert "IDLStruct" in out
    assert "IDLField" in out
    assert "import OMGIDL" in out


def test_attribute_definition():
    a = Attribute(definition=True)._set_name("mass")

    text = """attribute def mass;"""

    q = classtree(loads(text))

    assert a.dump() == q.dump()


def test_attribute_units():
    a = Attribute()._set_name("mass")
    a.set_value(100 * ureg.kg)

    text = """attribute mass= 100 [kilogram];"""

    q = classtree(loads(text))

    assert a.dump() == q.dump()


def test_attribute_getunits():
    value = 100 * ureg.kg

    a = Attribute()._set_name("mass")
    a.set_value(value)

    assert value == a.get_value()


def test_attribute_nounits():
    a = Attribute()._set_name("mass")
    a.set_value(100)

    text = """attribute mass= 100;"""

    q = classtree(loads(text))

    assert a.dump() == q.dump()


# ---------------------------------------------------------------------------
# Requirement nesting — children populated from grammar
# ---------------------------------------------------------------------------

def test_requirement_nested_children_populated():
    """A nested requirement usage should appear in the parent's .children."""
    import sysmlpy
    text = """package P {
        requirement def TopReq {
            subject s : Item;
            require constraint { s > 0 }
            requirement nested {
                subject t : Item;
                require constraint { t < 100 }
            }
        }
    }"""
    m = sysmlpy.loads(text)
    top = m.children[0].children[0]
    assert top.__class__.__name__ == "Requirement"
    assert top.name == "TopReq"
    assert len(top.children) == 1
    nested = top.children[0]
    assert nested.__class__.__name__ == "Requirement"
    assert nested.name == "nested"
    assert nested.parent is top


def test_requirement_multiple_nested_children():
    """Multiple nested requirements are all populated, in order."""
    import sysmlpy
    text = """package P {
        requirement engineSpecification {
            subject engine : Engine;
            requirement drivePowerInterface : DrivePowerInterface {
                subject = engine.clutchPort;
            }
            requirement torqueGeneration : TorqueGeneration {
                subject = engine.generateTorque;
            }
        }
    }"""
    m = sysmlpy.loads(text)
    eng = m.children[0].children[0]
    assert eng.name == "engineSpecification"
    names = [c.name for c in eng.children]
    assert names == ["drivePowerInterface", "torqueGeneration"]
    for c in eng.children:
        assert c.parent is eng


def test_requirement_deeply_nested_children():
    """Nested-of-nested requirements recurse through load_from_grammar."""
    import sysmlpy
    text = """package P {
        requirement def Outer {
            requirement mid {
                requirement inner {
                    subject x : Item;
                    require constraint { x > 0 }
                }
            }
        }
    }"""
    m = sysmlpy.loads(text)
    outer = m.children[0].children[0]
    assert outer.name == "Outer"
    mid = outer.children[0]
    assert mid.name == "mid"
    assert mid.parent is outer
    inner = mid.children[0]
    assert inner.name == "inner"
    assert inner.parent is mid
    assert inner.parent.parent is outer


def test_requirement_no_nested_children():
    """A flat requirement has an empty children list."""
    import sysmlpy
    text = """package P {
        requirement def Flat {
            subject s : Item;
            require constraint { s > 0 }
        }
    }"""
    m = sysmlpy.loads(text)
    flat = m.children[0].children[0]
    assert flat.name == "Flat"
    assert flat.children == []


def test_requirement_nested_children_preserves_grammar_roundtrip():
    """Populating children must not break grammar-object round-trip."""
    text = """package P {
        requirement vehicleSpecification {
            doc /* Overall vehicle requirements group */
            subject vehicle : Vehicle;
            require fullVehicleMassLimit;
            require emptyVehicleMassLimit;
        }
        requirement engineSpecification {
            doc /* Engine power requirements group */
            subject engine : Engine;
            requirement drivePowerInterface : DrivePowerInterface {
                subject = engine.clutchPort;
            }
            requirement torqueGeneration : TorqueGeneration {
                subject = engine.generateTorque;
            }
        }
    }"""
    # Grammar round-trip via load_grammar (raw dict) + classtree
    raw = loads(text)
    assert strip_ws(text) == strip_ws(classtree(raw).dump())
    # Public API: children should be populated
    import sysmlpy
    m = sysmlpy.loads(text)
    eng = m.children[0].children[1]
    assert eng.name == "engineSpecification"
    assert len(eng.children) == 2


# ---------------------------------------------------------------------------
# Typed-by preservation on load_from_grammar (v0.57.0)
# ---------------------------------------------------------------------------

def _find_by_name(root, name):
    if getattr(root, 'name', None) == name:
        return root
    for c in getattr(root, 'children', []) or []:
        r = _find_by_name(c, name)
        if r is not None:
            return r
    return None


def test_typed_by_name_preserved_part():
    import sysmlpy
    text = """package P {
        part def Engine;
        part def Vehicle {
            part engine : Engine;
        }
    }"""
    m = sysmlpy.loads(text)
    eng = _find_by_name(m, "engine")
    assert eng is not None
    assert eng.typed_by_name == "Engine"
    assert eng._typed_by_name == "Engine"


def test_typed_by_name_preserved_qualified_type():
    import sysmlpy
    text = """package P {
        part def Vehicle {
            attribute mass : ScalarValues::Real;
        }
    }"""
    m = sysmlpy.loads(text)
    mass = _find_by_name(m, "mass")
    assert mass is not None
    assert mass.typed_by_name == "ScalarValues::Real"


def test_typed_by_name_preserved_across_usage_kinds():
    import sysmlpy
    text = """package P {
        item def Fuel;
        port def SupplyPort;
        action def ComputeAct;
        interface def DataIface;
        part def Vehicle {
            item fuel : Fuel;
            port supply : SupplyPort;
            action compute : ComputeAct;
            interface link : DataIface;
        }
    }"""
    m = sysmlpy.loads(text)
    expected = {
        "fuel": "Fuel",
        "supply": "SupplyPort",
        "compute": "ComputeAct",
        "link": "DataIface",
    }
    for name, want in expected.items():
        el = _find_by_name(m, name)
        assert el is not None, f"{name} missing from model tree"
        assert el.typed_by_name == want, (
            f"{name}: typed_by_name={el.typed_by_name!r}, want {want!r}"
        )


def test_typed_by_name_none_without_typing():
    import sysmlpy
    text = """package P {
        part def Engine;
        part def Vehicle {
            part bare;
        }
    }"""
    m = sysmlpy.loads(text)
    bare = _find_by_name(m, "bare")
    assert bare is not None
    assert bare.typed_by_name is None


def test_typed_by_name_behavior_children():
    import sysmlpy
    text = """package P {
        state def Mode;
        part def Vehicle {
            state active : Mode;
        }
    }"""
    m = sysmlpy.loads(text)
    veh = _find_by_name(m, "Vehicle")
    states = [c for c in veh.children if type(c).__name__ == "State"]
    assert len(states) == 1
    assert states[0].typed_by_name == "Mode"


def test_typed_by_name_default_instance():
    # Programmatically-built elements default to None without errors
    p = Part(name="x")
    assert p.typed_by_name is None
    a = Attribute(name="y")
    assert a.typed_by_name is None


def test_typed_by_name_dump_roundtrip_unchanged():
    import sysmlpy
    text = """package P {
        part def Engine;
        part def Vehicle {
            part engine : Engine;
            attribute mass : ScalarValues::Real;
        }
    }"""
    m = sysmlpy.loads(text)
    strip = lambda s: "".join(s.split())
    assert strip(m.dump()) == strip(text)


# ---------------------------------------------------------------------------
# Multiplicity ordered/nonunique flags on round-trip (v0.59.0)
# ---------------------------------------------------------------------------

def test_multiplicity_ordered_flag_round_trip():
    """`ordered` keyword must survive loads() -> dump()."""
    import sysmlpy
    text = """package P {
        attribute x[3] ordered;
    }"""
    m = sysmlpy.loads(text)
    strip = lambda s: "".join(s.split())
    assert strip(m.dump()) == strip(text)


def test_multiplicity_nonunique_flag_round_trip():
    import sysmlpy
    text = """package P {
        attribute x[3] nonunique;
    }"""
    m = sysmlpy.loads(text)
    strip = lambda s: "".join(s.split())
    assert strip(m.dump()) == strip(text)


def test_multiplicity_ordered_nonunique_together():
    import sysmlpy
    text = """package P {
        attribute x[3] ordered nonunique;
    }"""
    m = sysmlpy.loads(text)
    strip = lambda s: "".join(s.split())
    assert strip(m.dump()) == strip(text)


def test_multiplicity_flags_preserved_in_grammar_object():
    import sysmlpy
    m = sysmlpy.loads("package P { attribute x[3] ordered nonunique; }")
    attr = m.children[0].children[0]
    spec = attr.grammar.usage.declaration.declaration.specialization
    assert spec.multiplicity is not None
    assert spec.multiplicity.isOrdered is True
    assert spec.multiplicity.isNonunique is True


def test_multiplicity_flags_on_part_usage():
    import sysmlpy
    text = """package P {
        part w[4] ordered;
    }"""
    m = sysmlpy.loads(text)
    strip = lambda s: "".join(s.split())
    assert strip(m.dump()) == strip(text)


def test_multiplicity_no_flags_regression():
    # Plain bounds remain untouched (no spurious keywords)
    import sysmlpy
    m = sysmlpy.loads("""package P {
        attribute y[5..2];
    }""")
    out = m.dump()
    assert "ordered" not in out and "nonunique" not in out
    assert "y[5..2]" in out.replace(" ", "") or "y[5..2]" in out


def test_toplevel_multiplicity_bounds_preserved():
    """Original STATUS.md bug report: top-level attribute x[5..2]."""
    import sysmlpy
    m = sysmlpy.loads("""package P { attribute x[5..2]; }""")
    attr = m.children[0].children[0]
    spec = attr.grammar.usage.declaration.declaration.specialization
    assert spec is not None and spec.multiplicity is not None
    strip = lambda s: "".join(s.split())
    assert strip(m.dump()) == strip("package P { attribute x[5..2]; }")


def test_classtree_accepts_model_object():
    """v0.78.0: classtree(loads(text)) — the documented Model form —
    must work, not raise TypeError. Previously only the grammar-dict
    form (load_grammar) worked."""
    from sysmlpy import loads
    from sysmlpy.formatting import classtree

    text = """package P {
    part def E;
    part e1 : E { attribute mass = 100 [kg]; }
}"""
    tree = classtree(loads(text))
    out = tree.dump()
    assert "part def E" in out
    assert "part e1: E" in out


def test_reference_set_type_renders():
    """v0.78.0: Reference.dump() renders ": Type" even when the
    typed-by element has no children (falsy via Searchable.__len__)."""
    from sysmlpy import Item, Reference

    person = Item(name="Person")
    r = Reference(name="driver")
    r.set_type(person)
    assert r.dump() == "ref driver : Person;"

    r2 = Reference(name="payload", redefines=True)
    r2.set_type(person)
    assert r2.dump() == "ref :>> payload : Person;"
