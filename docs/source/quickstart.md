Quick Start
==========

This guide explains sysml2py through working examples derived from the test suite.

Installation
------------

::

    pip install sysml2py

Or from source::

    pip install -e .


Basic Workflow
-------------

sysml2py provides two-way translation between SysML v2 text and Python objects:

1. **Parse SysML text → Python object** using ``load_grammar()``
2. **Build Python object → SysML text** using ``.dump()``

::

    from sysml2py import Package, load_grammar as loads
    from sysml2py.formatting import classtree

    # Parse text to Python
    text = "package Rocket;"
    pkg = loads(text)
    
    # Python to text
    output = classtree(pkg).dump()
    # → "package Rocket;"

Packages
--------

Create a package::

    from sysml2py import Package

    p = Package()._set_name("Rocket")
    print(p.dump())
    # → "package Rocket;"

Package with body::

    p = Package(name="Rocket")
    p._set_child(Package(name="Engine"))
    print(p.dump())
    # → package Rocket {
    #        package Engine;
    #     }

Short names (alias IDs)::

    p = Package(name="Rocket", shortname="'3.1'")
    print(p.dump())
    # → package <'3.1'> Rocket;

Items
-----

Create an item usage::

    from sysml2py import Item

    i = Item(name="Fuel")
    print(i.dump())
    # → item Fuel;

Item definition::

    i = Item(definition=True, name="Fuel")
    print(i.dump())
    # → item def Fuel;

Items with children::

    i = Item(name="Fuel")
    i._set_child(Item(name="Oxidizer"))
    print(i.dump())
    # → item Fuel {
    #        item Oxidizer;
    #     }

Parts
-----

Parts work like items::

    from sysml2py import Part

    p = Part(name="Engine")
    print(p.dump())
    # → part Engine;

Attributes
-----------

Attributes with values::

    from sysml2py import Attribute, ureg

    a = Attribute(name="mass")
    a.set_value(100 * ureg.kilogram)
    print(a.dump())
    # → attribute mass = 100 [kilogram];

Composite structures::

    from sysml2py import Part, Attribute

    p = Part(name="Stage1")
    p._set_child(Attribute(name="mass"))
    p._set_child(Attribute(name="thrust"))
    print(p.dump())
    # → part Stage1 {
    #        attribute mass;
    #        attribute thrust;
    #     }

Typing (Subclassing)
------------------

An item can be typed by a definition::

    from sysml2py import Item

    # Create definition
    fuel_def = Item(definition=True, name="Fuel")
    
    # Create usage typed by definition
    hydrogen = Item(name="Hydrogen")
    hydrogen._set_typed_by(fuel_def)
    print(hydrogen.dump())
    # → item Hydrogen : Fuel;

Model
-----

A Model contains packages::

    from sysml2py import Model, Package

    m = Model()
    m._set_child(Package(name="Rocket"))
    m._set_child(Package(name="Payload"))
    print(m.dump())
    # → package Rocket;
    #     package Payload;

Loading full text
-----------------

Parse complete SysML text::

    from sysml2py import Model

    text = """package Rocket {
           item def Fuel;
           item Hydrogen : Fuel;
        }"""

    model = Model().load(text)
    print(model.dump())

Reference
---------

For more examples, see the test files in ``tests/class_test.py``.

Python Representation
------------------

All classes have ``__repr__`` that returns constructor-style output::

    from sysml2py import Package, Item, Part, Attribute

    p = Package(name='Rocket')
    print(repr(p))
    # → Package(name='Rocket')

    i = Item(definition=True, name='Fuel')
    print(repr(i))
    # → Item(definition=True, name='Fuel')

    part = Part(name='Engine')
    print(repr(part))
    # → Part(name='Engine')

    attr = Attribute(name='mass')
    print(repr(attr))
    # → Attribute(name='mass')

Anonymous elements show a UUID until named::

    from sysml2py import Package
    p = Package()
    print(repr(p))
    # → Package(name='a1b2c3d4-...')  # UUID