# sysmlpy Tutorial

A guide to using `sysmlpy` — a pure Python library for constructing and parsing SysML v2.0 models.

## Installation

```bash
pip install sysmlpy
```

## Quick Start

```python
from sysmlpy import loads, Model, Package, Part, Attribute, ureg

# Parse SysML text
model = loads("""
package MyModel {
    part def Engine;
    part engine1: Engine {
        attribute mass = 100 [kg];
    }
}
""")

# Or build programmatically
p = Part(name="Stage_1", shortname="'3.1'")
a = Attribute(name="mass")
a.set_value(100 * ureg.kilogram)
p.add_child(a)
print(p.dump())
# → part <'3.1'> Stage_1 { attribute mass = 100 [kilogram]; }
```

## Architecture

`sysmlpy` has three layers:

1. **Public API** (`usage.py`) — Python classes you use directly: `Part`, `Item`, `Action`, `State`, etc.
2. **Grammar Layer** (`grammar/classes.py`) — ~319 internal classes that mirror the ANTLR parse tree. Used for round-trip parsing.
3. **ANTLR Parser** (`antlr/`, `antlr_visitor.py`) — Parses SysML v2 text into an internal dict, then into grammar objects.

```
SysML text → ANTLR Lexer/Parser → Visitor → dict → Grammar Classes → Public API Classes
```

## SysML v2 to Python Mapping

### Base Classes

| Python Class | Role | Key Methods |
|---|---|---|
| `Searchable` | Mixin — `find()`, `all()`, typed property accessors | `find(name, sysml_type, recursive)`, `find_one()`, `parts`, `actions`, `states`, etc. |
| `Usage` | Base for all usage/definition wrappers | `dump()`, `load_from_grammar()`, `add_child()`, `set_typed_by()`, `set_specializes()`, `set_subsets()`, `set_redefines()` |
| `Model` | Root container | `load(s)`, `dump()` |
| `Package` | Namespace container | `load_from_grammar()`, `dump()` |
| `Transition` | State machine transition (standalone) | `load_from_grammar()`, `source`, `trigger`, `guard`, `target`, `effect` |

### Structural Elements

| Python Class | SysML Keywords | Def/Usage | Grammar Class | `load_from_grammar` |
|---|---|---|---|---|
| `Part` | `part`, `part def` | Both | `PartUsage`, `PartDefinition` | Yes |
| `Item` | `item`, `item def` | Both | `ItemUsage`, `ItemDefinition` | Yes |
| `Attribute` | `attribute`, `attribute def` | Both | `AttributeUsage`, `AttributeDefinition` | Yes |
| `Port` | `port`, `port def` | Both | `PortUsage`, `PortDefinition` | Yes |
| `Connection` | `connection`, `connection def` | Both | `ConnectionUsage`, `ConnectionDefinition` | Yes (via Package) |
| `Flow` | `flow`, `flow def` | Both | `FlowConnectionUsage`, `FlowConnectionDefinition` | Yes (via Package) |
| `FlowDef` | `flow def` | Def only | `FlowDefinition` | No |
| `Allocation` | `allocation`, `allocation def` | Both | `AllocationUsage`, `AllocationDefinition` | Yes (via Package) |
| `Individual` | `individual`, `individual def` | Both | `IndividualUsageSimple`, `IndividualDefinition` | Yes (via Package) |

### Behavioral Elements

| Python Class | SysML Keywords | Def/Usage | Grammar Class | `load_from_grammar` |
|---|---|---|---|---|
| `Action` | `action`, `action def` | Both | `ActionUsage`, `ActionDefinition` | Yes (custom) |
| `State` | `state`, `state def` | Both | `StateUsage`, `StateDefinition` | Yes (custom) |
| `Transition` | `transition`, `then`, `entry` | N/A | `TransitionUsage`, `TargetTransitionUsage` | Yes (standalone) |

### Requirements

| Python Class | SysML Keywords | Def/Usage | Grammar Class | `load_from_grammar` |
|---|---|---|---|---|
| `Requirement` | `requirement`, `requirement def` | Both | `RequirementUsage`, `RequirementDefinition` | Yes (via Package) |
| `UseCase` | `use case`, `use case def` | Both | `UseCaseUsage`, `UseCaseDefinition` | Yes (via Package) |

### Cases

| Python Class | SysML Keywords | Def/Usage | Grammar Class | `load_from_grammar` |
|---|---|---|---|---|
| `Case` | `case`, `case def` | Both | `CaseUsage`, `CaseDefinition` | Yes (via Package) |
| `AnalysisCase` | `analysis`, `analysis def` | Both | `AnalysisCaseUsage`, `AnalysisCaseDefinition` | Yes (via Package) |
| `VerificationCase` | `verification`, `verification case def` | Both | `VerificationCaseUsage`, `VerificationCaseDefinition` | Yes (via Package) |

### Constraints & Calculations

| Python Class | SysML Keywords | Def/Usage | Grammar Class | `load_from_grammar` |
|---|---|---|---|---|
| `Constraint` | `constraint`, `constraint def` | Both | `ConstraintUsage`, `ConstraintDefinition` | Yes (via Package) |
| `Calculation` | `calc`, `calc def` | Both | `CalculationUsage`, `CalculationDefinition` | Yes (via Package) |

### Views & Viewpoints

| Python Class | SysML Keywords | Def/Usage | Grammar Class | `load_from_grammar` |
|---|---|---|---|---|
| `View` | `view`, `view def` | Both | `ViewUsage`, `ViewDefinition` | Yes (via Package) |
| `Viewpoint` | `viewpoint`, `viewpoint def` | Both | `ViewpointUsage`, `ViewpointDefinition` | Yes (via Package) |
| `Concern` | `concern`, `concern def` | Both | `ConcernUsage`, `ConcernDefinition` | Yes (via Package) |

### Metadata & Rendering

| Python Class | SysML Keywords | Def/Usage | Grammar Class | `load_from_grammar` |
|---|---|---|---|---|
| `Metadata` | `metadata`, `metadata def` | Both | `MetadataUsage`, `MetadataDefinition` | Yes (via Package) |
| `Rendering` | `rendering`, `rendering def` | Both | `RenderingUsage`, `RenderingDefinition` | Yes (via Package) |
| `Enumeration` | `enum def` | Def only | `EnumerationDefinition` | Yes (via Package) |

### Custom (No Grammar Backing)

| Python Class | SysML Keywords | Notes |
|---|---|---|
| `Interface` | `interface`, `interface def` | Custom Python implementation, grammar wrapper only |
| `Message` | `message` | Custom Python implementation |
| `Reference` | `ref` | Custom Python implementation |
| `DefaultReference` | `in`/`out`/`inout ref` | Grammar-backed via `DefaultReferenceUsage` |

## Usage Examples

### Building Parts Programmatically

```python
from sysmlpy import Part, Item, Attribute, ureg

# Create a sensor part with children
sensor = Part(name="sensor")
camera = Part(name="camera")
lens = Item(name="lens")
mass = Attribute(name="mass")
mass.set_value(100 * ureg.kilogram)

camera.add_child(mass)
sensor.add_child(camera)
sensor.add_child(lens)

print(sensor.dump())
# part sensor {
#     part camera {
#         attribute mass = 100 [kilogram];
#     }
#     item lens;
# }
```

### Actions with Inputs and Outputs

```python
from sysmlpy import Action

# Action definition
a = Action(definition=True, name="Focus")
a.add_input("scene", "Scene")
a.add_output("image", "Image")
print(a.dump())
# → action def Focus { in scene : Scene; out image : Image; }

# Action usage
b = Action(name="TakePicture")
b.add_input("scene")
b.add_output("picture")
print(b.dump())
# → action TakePicture { in scene; out picture; }
```

### References

```python
from sysmlpy import Reference, Item

# Simple reference
r = Reference(name="driver")
print(r.dump())
# → ref driver;

# Typed reference
person = Item(name="Person")
r2 = Reference(name="driver")
r2.set_type(person)
print(r2.dump())
# → ref driver : Person;

# Reference redefinition
r3 = Reference(name="payload", redefines=True)
r3.set_type(person)
print(r3.dump())
# → ref :>> payload : Person;
```

#### Specialization keywords on usages (v0.40.0+)

SysML v2 has four specialization kinds, and all of them round-trip on any
usage — attributes, parts, actions, requirements, and more:

| Source form | Meaning | Grammar relationship |
|---|---|---|
| `: TypeName` | typing | `Typings` |
| `:> Base` / `subsets Base` | subsetting | `Subsettings` |
| `:>> Base` / `redefines Base` | redefinition | `Redefinitions` |
| `::> T` / `references T` | type-only reference | `References` |

```python
from sysmlpy import loads

model = loads("""package P {
    action a1 :> BaseType;
    action a2 ::> RefType;
    action a3 references OtherType;   # keyword form
    action a4 :>> RedefType;
    action a5 : Real;
}""")

def find_actions(node):
    out = []
    if type(node).__name__ == 'Action':
        out.append(node)
    for c in getattr(node, 'children', []):
        out.extend(find_actions(c))
    return out

for a in find_actions(model):
    print(a.dump())
# → action a1 :> BaseType;
# → action a2 ::> RefType;
# → action a3 ::> OtherType;   # keyword canonicalizes to operator form
# → action a4 :>> RedefType;
# → action a5 : Real;
```

### Parsing and Round-Trip

```python
from sysmlpy import loads
from sysmlpy.formatting import classtree

text = """package 'Action Example' {
    action def Focus { in scene : Scene; out image : Image; }
    action TakePicture {
        in item scene : Scene;
        out item picture : Picture;
        action focus : Focus { in scene; out image; }
    }
}"""

model = loads(text)
tree = classtree(model)
print(tree.dump())
```

### Redeclared Feature Names (v0.39.0+)

When a usage re-declares a feature (`:>>`, `:>`, `::>`) without its own
identification, the user-visible name lives in the specialization chain —
not on the feature declaration. Two helpers surface it:

```python
from sysmlpy import loads

text = """package DummyUsageModel {
    private import DummyDefinitionModel::*;
    view def ViewUsage :> ViewDefinition {
        attribute :>> exampleAttribute = "Example Value";
    }
}"""
model = loads(text)
view = model.get_child("DummyUsageModel.ViewUsage")
attr = view.attributes[0]

print(attr.get_value())       # → Example Value
print(attr.dump())            # → attribute :>> exampleAttribute= "Example Value";
print(attr.name)              # → 'd68f2dc6-...'  (UUID sentinel, unchanged)
print(attr.redefined_name)    # → 'exampleAttribute'
print(attr.display_name)      # → 'exampleAttribute'
```

- **`redefined_name`** — last identifier segment of the first
  re-declaration chain; `""` when the element has none.
- **`display_name`** — user-meaningful name: returns `self.name` when it
  holds a real identifier, otherwise falls back to `redefined_name`,
  suppressing the UUID sentinel. Use it for UI / log output.

`self.name` deliberately stays the UUID sentinel so symbol resolution,
dump, and navigation behavior is preserved.

### State Machines

```python
from sysmlpy import State

# State definition
s = State(definition=True, name="Running")
print(s.dump())
# → state def Running;

# State with transitions (via grammar)
model = loads("""
package States {
    state def Engine {
        state off;
        state on {
            entry start;
            do run;
            exit stop;
        }
        transition off to on if key_turned;
    }
}
""")
```

### Requirements

```python
from sysmlpy import Requirement

r = Requirement(definition=True, name="PowerRequirement")
r.set_doc("The system shall provide sufficient power.")
r.add_constraint("Power output >= 1000W")
print(r.dump())
```

### Working with Units

```python
from sysmlpy import Attribute, ureg

a = Attribute(name="thrust")
a.set_value(1000 * ureg.newton)
print(a.get_value())  # 1000 newton
a.set_value(a.get_value() + 199 * ureg.newton)
print(a.dump())  # attribute thrust = 1199.0 [newton];
```

## Model Navigation (v0.30.2+)

These methods are available on `Model`, `Package`, and every usage node for navigating and analyzing models.

### find

Recursively find matching elements with flexible filtering:

```python
from sysmlpy import loads, Part

model = loads("""
package Vehicle {
    part def Engine;
    part engine1: Engine {
        attribute mass = 100 [kg];
    }
    part chassis {
        part wheel1;
        part wheel2;
    }
}
""")

# Find by type string using sysml_type=
all_parts = model.find(sysml_type="part")
print(f"Found {len(all_parts)} parts: {[p.name for p in all_parts]}")
# → Found 4 parts: ['engine1', 'chassis', 'wheel1', 'wheel2']

# Find by class
all_parts = model.find(sysml_type=Part)

# Find by name (single or ambiguous)
engine = model.find_one("engine1")  # returns element or None
assert engine is not None

# find_one() raises LookupError on multiple matches
# model.find_one("wheel")  → LookupError: 2 matches

# Shorthand for all parts
all_parts = model.all("part")
```

### count

Count elements by type across the full tree:

```python
# Count specific type
part_count = model.count('part')
print(f"Parts: {part_count}")  # → Parts: 4

# Count all types
counts = model.count()
print(counts)
# → {'part': 4, 'attribute': 1}
```

### traverse

Walk the element tree with a callback function:

```python
# Print tree structure with indentation
def print_tree(elem, depth):
    name = getattr(elem, 'name', '?')
    stype = getattr(elem, 'sysml_type', '')
    indent = "  " * depth
    print(f"{indent}{stype}: {name}")

model.traverse(print_tree)
# → package: Vehicle
# →   part: engine1
# →     attribute: mass
# →   part: chassis
# →     part: wheel1
# →     part: wheel2
```

### to_dict

Export the model as a nested dictionary:

```python
d = model.to_dict()
print(list(d.keys()))
# → ['name', 'children']

import json
print(json.dumps(d, indent=2, default=str))
# {
#   "name": "Model",
#   "children": [
#     {
#       "name": "Vehicle",
#       "sysml_type": "package",
#       "children": [...]
#     }
#   ]
# }
```

### to_graph

Export the model to a NetworkX graph for analysis:

```python
# Requires: pip install sysmlpy[graph]
store = model.to_graph()

# Graph statistics
print(store.stats())
# → {'nodes': 7, 'edges': 6, 'density': 0.286, ...}

# Find connected components
components = store.connected_components()
print(f"Connected components: {len(components)}")

# Find cycles (useful for detecting circular type references)
cycles = store.cycles()
print(f"Cycles: {len(cycles)}")

# Node centrality (which elements have the most connections)
centrality = store.centrality()
top = sorted(centrality.items(), key=lambda x: x[1], reverse=True)[:3]
for eid, score in top:
    data = store.get(eid)
    print(f"  {data['name']}: {score:.3f}")

# Export to GraphML for visualization in Gephi or Cytoscape
store.export_graphml("model.graphml")
```

### path_between

Find the path between two elements by name:

```python
# Path from parent to child
path = model.path_between('chassis', 'wheel1')
print(path)
# → ['chassis', 'wheel1']

# Path between siblings (goes through common parent)
path = model.path_between('wheel1', 'wheel2')
print(path)
# → ['wheel1', 'chassis', 'wheel2']

# No path returns None
path = model.path_between('engine1', 'nonexistent')
print(path)  # → None
```

## Partial Parse Recovery (v0.38.0+)

By default `loads` / `load` raise `SysMLSyntaxError` on malformed input.
When you want to keep whatever *did* parse — e.g. linting a file the spec
rejects, or triaging a broken model — use the `_partial` variants:

```python
from sysmlpy import loads_partial, load_partial, PartialParseError

# Canonical example: a visibility-less `import ScalarValues;`
text = """package ImportVisibility {
    public import ScalarValues;
    private import ScalarValues;
    protected import ScalarValues;
    import ScalarValues;              # <- rejected by the grammar
}"""

try:
    model = load_partial(text)
except PartialParseError as e:
    print(len(e.errors))       # → 1  ("Syntax error at 5:4: extraneous input 'import' ...")
    print(e.partial is not None)  # → True

    from sysmlpy.formatting import classtree
    print(classtree(e.partial).dump())
    # package ImportVisibility {
    #    public import ScalarValues;
    #    private import ScalarValues;
    #    protected import ScalarValues;
    # }
```

- `loads_partial(text)` returns the visitor **dict** (raising
  `PartialParseError` with `.partial` on errors).
- `load_partial(text)` returns the typed **Model** on success.
- The strict `loads` / `load` are unchanged.

## Loading Functions

| Function | Description |
|---|---|
| `loads(text)` | Parse SysML v2 text string into a `Model` |
| `load(file)` | Parse SysML v2 file into a `Model` |
| `parse(text)` | Parse SysML v2 text into `(Model, errors)` tuple — never raises |
| `loads_partial(text)` | Like `loads`, but raises `PartialParseError` (carrying `.partial`) instead of aborting |
| `load_partial(file)` | Like `load`, but raises `PartialParseError` (carrying `.partial`) instead of aborting |
| `load_grammar(text)` | Parse into grammar dict (internal) |
| `load_antlr(text)` | Explicit ANTLR4 parsing path |
| `load_grammar_antlr(text)` | Parse into grammar dict via ANTLR4 |

## Conformance

**100% of 123 OMG XPect conformance tests pass** (123/123).

Run the full suite:
```bash
pytest -m conformance
```
