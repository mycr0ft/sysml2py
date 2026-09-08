"""Examples: Tuples and Sequences in SysML v2

SysML v2 supports tuples/sequences for collections. This document explains
the syntax and current status in sysmlpy.
"""

from sysmlpy import loads, Part, Attribute

# =============================================================================
# 1. Tuple Syntax in SysML v2
# =============================================================================

# SysML v2 uses parentheses with commas for tuples:
#   attribute point : Anything[2] = (10, 20);
#   attribute rgb : Anything[3] = (255, 128, 0);

# =============================================================================
# 2. Using Collections Library Types
# =============================================================================

# The Collections library (kernel/Collections.kerml) provides:
#   - Array: Fixed-size multi-dimensional collection
#   - List: Variable-size ordered collection
#   - Set: Variable-size unordered unique collection
#   - Bag: Variable-size unordered non-unique collection
#   - Map: Collection of key-value pairs
#   - KeyValuePair: A tuple of (key, value)

print("=" * 60)
print("Tuples and Sequences in SysML v2 - sysmlpy")
print("=" * 60)

# =============================================================================
# 3. Current Status
# =============================================================================

print("\n3. Current Status")
print("-" * 40)

# Simple values: WORKING
print("\nSimple values (Integer, Real, String, Boolean):")
model = loads('''
package Example {
    attribute count : Integer = 42;
    attribute price : Real = 19.99;
    attribute name : String = "Widget";
    attribute mass : Real = 100 [kilogram];
}
''')
pkg = model.children[0]
for attr in pkg.children:
    try:
        val = attr.get_value()
        print(f"  {attr.name} = {val}")
    except Exception as e:
        print(f"  {attr.name}: ERROR - {type(e).__name__}")

# Tuples: PARTIAL (parse succeeds but value extraction needs work)
print("\nTuples like (10, 20):")
try:
    model = loads('''
    package Example {
        attribute point : Real[2] = (10, 20);
    }
    ''')
    print("  SUCCESS - tuple parsing works!")
except Exception as e:
    print(f"  FAILED - {type(e).__name__}")
    print("  (Known limitation: tuple syntax not yet fully supported)")

# =============================================================================
# 4. Recommended Workaround: Use Parts Instead of Tuples
# =============================================================================

print("\n4. Recommended Workaround: Use Parts with Named Fields")
print("-" * 40)

# Instead of tuples, use parts with named attributes:
model = loads('''
package Example {
    /** A 2D position using a Part */
    part def Position2D {
        attribute x : Real = 10;
        attribute y : Real = 20;
    }
    
    /** RGB Color using a Part */
    part def RGBColor {
        attribute red : Integer = 255;
        attribute green : Integer = 128;
        attribute blue : Integer = 0;
    }
    
    /** A vehicle with position and color */
    part def Vehicle {
        attribute mass : Real = 1000 [kilogram];
        part position : Position2D;
        part bodyColor : RGBColor;
    }
}
''')

# Get parts directly
parts = [c for c in model.children[0].children if isinstance(c, Part)]
print("\nPackage contents:")
for part in parts:
    print(f"  Part: {part.name}")

# Find Vehicle
vehicle = next((p for p in parts if p.name == 'Vehicle'), None)
if vehicle:
    print(f"\nVehicle '{vehicle.name}':")
    for child in vehicle.children:
        if isinstance(child, Attribute):
            try:
                print(f"  {child.name} = {child.get_value()}")
            except Exception as e:
                print(f"  {child.name}: (get_value pending)")
        elif isinstance(child, Part):
            print(f"  {child.name}:")
            for subchild in child.children:
                if isinstance(subchild, Attribute):
                    try:
                        print(f"    {subchild.name} = {subchild.get_value()}")
                    except Exception:
                        pass

# =============================================================================
# 5. Alternative: Use Multiple Attributes
# =============================================================================

print("\n5. Alternative: Use Multiple Single-Value Attributes")
print("-" * 40)

model = loads('''
package Example {
    part def TemperatureReading {
        attribute reading1 : Real;
        attribute reading2 : Real;
        attribute reading3 : Real;
    }
    
    part sensor1 : TemperatureReading {
        reading1 = 22.5 [degC];
        reading2 = 23.0 [degC];
        reading3 = 21.5 [degC];
    }
}
''')

pkg = model.children[0]
parts = [c for c in pkg.children if isinstance(c, Part)]
sensor = next((p for p in parts if p.name == 'sensor1'), None)
if sensor:
    print(f"\nTemperature readings for '{sensor.name}':")
    for attr in sensor.children:
        if isinstance(attr, Attribute):
            try:
                print(f"  {attr.name} = {attr.get_value()}")
            except Exception:
                pass

# =============================================================================
# 6. Collections Library Reference
# =============================================================================

print("\n6. Collections Library Reference")
print("-" * 40)

print("""
The kernel/Collections.kerml library provides these types:

  datatype Collection          - Base collection type with 'elements' feature
  datatype OrderedCollection   - Ordered collections
  datatype UniqueCollection   - Collections with unique elements
  
  datatype Array              - Fixed-size multi-dimensional collection
                              - Use 'dimensions' to specify shape
                              - Use 'elements' for flattened access
  
  datatype List               - Variable-size ordered collection
  datatype Set                - Variable-size unordered unique collection
  datatype Bag                - Variable-size unordered non-unique collection
  
  datatype Map                - Collection of key-value pairs
  datatype KeyValuePair       - A tuple of (key, value)
  
  datatype OrderedMap         - Ordered map

Example usage in SysML:
  import Collections::*;
  
  attribute measurements : List = #("temp1", "temp2", "temp3");
  attribute dataPoint : KeyValuePair = (key = "x", val = 10);
""")

# =============================================================================
# 7. Summary
# =============================================================================

print("\n" + "=" * 60)
print("Summary: Tuple/Sequence Support in sysmlpy")
print("=" * 60)
print("""
+---------------------------+------------+
| Feature                   | Status     |
+---------------------------+------------+
| Simple values             | WORKS      |
|   Integer, Real, String   |            |
| Pint quantities           | WORKS      |
|   Real = 100 [kilogram]   |            |
| Tuples                     | PARTIAL    |
|   (10, 20, 30)           | (parses)   |
| Lists with #()           | NOT YET    |
|   #("a", "b", "c")        |            |
+---------------------------+------------+

Workarounds:
1. Use structured types (parts) instead of tuples
2. Use multiple single-value attributes
3. Use Parts with named fields for complex data

Recommended pattern:
  part def Position2D {
      attribute x : Real;
      attribute y : Real;
  }
  
  part origin : Position2D { x = 10; y = 20; }
""")