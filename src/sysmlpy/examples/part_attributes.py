"""Examples: Checking Attributes of a Part

NOTE: Currently, children are only loaded for 'part def' (definitions).
      Using 'part' (usage) may not load nested children - this is a known limitation.
"""

from sysmlpy import loads, Part, Attribute
from sysmlpy.usage import ureg

# =============================================================================
# 1. Basic Attribute Access
# =============================================================================

model = loads('''
package Example {
    part def Vehicle {
        attribute maxSpeed : Real;
        attribute mass : Real;
        part Engine { }
    }
}
''')

vehicle = model.children[0].children[0]

print("All children:", vehicle.children)

# Filter for attributes
attrs = [c for c in vehicle.children if isinstance(c, Attribute)]
print("Attributes:", [a.name for a in attrs])

# Filter for nested parts
nested_parts = [c for c in vehicle.children if isinstance(c, Part)]
print("Nested parts:", [p.name for p in nested_parts])

# =============================================================================
# 2. Attribute Properties
# =============================================================================

model = loads('''
package Example {
    part def Vehicle {
        attribute maxSpeed : Real;
        attribute mass : Real = 1000 [kilogram];
    }
}
''')

vehicle = model.children[0].children[0]

for attr in vehicle.children:
    print(f"\nAttribute: {attr.name}")
    print(f"  is_definition: {type(attr.grammar).__name__ == 'AttributeDefinition'}")
    print(f"  grammar type: {type(attr.grammar).__name__}")

# =============================================================================
# 3. Working with Values (Single Values)
# =============================================================================

# NOTE: get_value() requires the attribute to have been set with a value
# and the valuepart to exist in the grammar. This is still being improved.

model = loads('''
package Example {
    part def Vehicle {
        attribute mass : Real = 1000 [kilogram];
        attribute name : String = "Tesla";
    }
}
''')

vehicle = model.children[0].children[0]

for attr in vehicle.children:
    try:
        val = attr.get_value()
        print(f"{attr.name} = {val}")
    except Exception as e:
        print(f"{attr.name}: get_value() needs valuepart - {type(e).__name__}")

# =============================================================================
# 4. Setting Values Programmatically
# =============================================================================

attr = Attribute()
attr._set_name("weight")

# Set with pint Quantity (recommended)
attr.set_value(1500 * ureg.kilogram)
print(f"\nAfter setting: {attr.get_value()}")

# NOTE: Setting with strings has a known bug where get_value() fails to parse.
# This will be fixed in a future update.
# attr.set_value("1200 [kilogram]")  # BUG: get_value() fails after string assignment

# =============================================================================
# 5. Checking Type
# =============================================================================

# NOTE (v0.57.0): the declared type name is preserved on load via
# `typed_by_name`; the resolved definition object (`typedby`) requires
# programmatic wiring via set_typed_by().

model = loads('''
package Example {
    part def Vehicle {
        attribute mass : Real;
        attribute name : String;
    }
}
''')

vehicle = model.children[0].children[0]

for attr in vehicle.children:
    if attr.typed_by_name:
        print(f"{attr.name} : {attr.typed_by_name}")
    else:
        # Access type from grammar structure
        print(f"{attr.name} : (type in grammar, typing not declared)")

# =============================================================================
# 6. Nested Parts
# =============================================================================

model = loads('''
package Example {
    part def Vehicle {
        attribute mass : Real;
        part Engine {
            attribute displacement : Real;
        }
    }
}
''')

vehicle = model.children[0].children[0]
engine = vehicle.children[1]  # Engine

print(f"\n{vehicle.name} contains: {[c.name for c in vehicle.children]}")
print(f"{engine.name} contains: {[c.name for c in engine.children]}")