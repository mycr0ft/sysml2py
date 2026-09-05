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
# → part <'3.1'> Stage_1 { attribute mass= 100[kilogram]; }
```

## Architecture

`sysmlpy` has four layers:

1. **Public API** (`usage.py`) — Python classes you use directly: `Part`, `Item`, `Action`, `State`, etc.
2. **Grammar Layer** (`grammar/classes.py`) — ~360 internal classes that mirror the ANTLR parse tree. Used for round-trip parsing.
3. **ANTLR Parser** (`antlr/`, `antlr_visitor.py`) — Parses SysML v2 text into an internal dict, then into grammar objects. Two-stage SLL→LL prediction keeps large models fast (identical trees, errors, and diagnostics).
4. **Analysis layer** (`semantic.py`, `store.py`, `plantuml.py`, `diff.py`) — semantic analysis, graph stores, view rendering, and model diffing.

```
SysML text → ANTLR Lexer/Parser → Visitor → dict → Grammar Classes → Public API Classes
                                                                        ↓
                                                       analyze() · stores · views · diff
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
        transition ignite first off accept KeyTurn then on;
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
print(a.dump())  # attribute thrust= 1199[newton];
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
# → Found 5 parts: ['Engine', 'engine1', 'chassis', 'wheel1', 'wheel2']
#   (find() is recursive and includes definitions)

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

Count elements by type across packages (non-recursive — direct
package children):

```python
# Count specific type
part_count = model.count('part')
print(f"Parts: {part_count}")  # → Parts: 3 (Engine, engine1, chassis)

# Count all types
counts = model.count()
print(counts)
# → {'part': 3}

# For a full recursive count, use find() with sysml_type=
len(model.find(sysml_type="part"))  # → 5
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
# → {'nodes': 7, 'edges': 6, 'density': 0.143,
#    'is_connected': True, 'avg_degree': 1.71}

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

## Semantic Analysis

Parsing only checks syntax. `analyze()` runs the full semantic
engine — 31 rule codes covering symbol resolution, imports, OCL
well-formedness, expression typing, and unit dimensions:

```python
from sysmlpy import loads, analyze

model = loads("""
    package Types {
        part def Engine;
    }
    package Vehicle {
        import Types::*;
        part myCar : Engine;    # resolved via import
        part myWheel : Wheel;   # undefined!
    }
""")

result = analyze(model)

for issue in result:
    print(f"[{issue.severity}] {issue.code}: {issue.message}")
# → [error] UNDEFINED_SYMBOL: Undefined symbol 'Wheel' referenced in Part 'myWheel'

result.errors          # errors only
result.warnings        # warnings only
bool(result)           # True when no errors (warnings are OK)
result.raise_on_errors()   # ValueError if any errors exist
len(result)            # total issue count (AnalysisResult is a list)
```

Highlights of what the analyzer checks:

- **Symbol resolution** — qualified names (`P::A`), imports
  (`import Types::*`, membership, `::**` recursion, visibility),
  inheritance chains
- **Expression validation** — operand types (`"a" + 5` is an error),
  unit compatibility (`[m] + [kg]`), and `*`/`/` dimension
  *derivation* (`[N]` inferred from `[kg] * [m/s^2]`)
- **OCL well-formedness** — duplicate names, cyclic specialization,
  subsetting/redefinition compatibility, part/port typing, feature
  chaining, multiplicity bounds
- **Structure checks** — connector ends (unresolved chains, direction
  wiring, port-definition compatibility), state machines, requirement
  subjects, traceability and verification coverage

The complete rule-code catalogue lives in [STATUS.md](STATUS.md).

## Model Diff

Compare two models semantically — additions, removals, and changed
signatures (typing, requirement subject, documentation):

```python
from sysmlpy import diff_models

old = loads(open("v1.sysml").read())
new = loads(open("v2.sysml").read())

d = diff_models(old, new)
d.is_empty()           # False when the models differ
d.added, d.removed, d.changed
print(d.as_text())     # +/-/~ unified text view
print(d.as_markdown()) # for release notes / PRs
# JSON output for tooling: sysmlpy diff old.sysml new.sysml --format json
```

Identity is `(kind, qualified name)` — repurposing a name across
roles reports removed + added rather than a silent change. The same
engine backs the CLI: `sysmlpy diff old.sysml new.sysml`.

## Command-Line Tools

Everything above is scriptable from the shell with CI-friendly exit
codes (`0` clean, `1` findings/error, `2` load failure):

```bash
sysmlpy analyze model.sysml        # semantic gate
sysmlpy diff old.sysml new.sysml   # semantic diff
sysmlpy view model.sysml           # PlantUML / Markdown / HTML views
sysmlpy format model.sysml         # canonicalize
sysmlpy trace model.sysml          # requirement traceability
sysmlpy export model.sysml         # JSON interchange
sysmlpy eval model.sysml           # evaluate expressions/values
sysmlpy sim model.sysml            # simulate a state machine
sysmlpy xlsx model.sysml           # Excel workbook of tabular views
```

See the [README CLI table](https://github.com/mycr0ft/sysmlpy#command-line-tools)
for all flags, and [sim.md](docs/sim.md) for simulation specifics.

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

## Storage Backends

Models can be exported to graph stores for analysis and persistence —
memory, NetworkX, Kùzu (embedded, Cypher), or Cayley (HTTP server):

```python
store = model.to_graph()          # NetworkX by default
print(store.stats())
store.export_graphml("model.graphml")

from sysmlpy.store import create_store
kuzu = create_store("kuzu", database="model.db")     # persists to disk
```

See the README's *Storage Backends* section for backend-by-backend
examples.

## Where to Go Next

| Topic | Document |
|-------|----------|
| Full feature walkthrough | [Quick Start](docs/quickstart.md) |
| Architecture & capabilities | [Project Summary](docs/PROJECT_SUMMARY.md) |
| Analyzer rule codes & conformance | [STATUS.md](STATUS.md) |
| State-machine simulation | [docs/sim.md](docs/sim.md) |
| Guard conditions (`if` vs `guard`) | [docs/GUARDS.md](docs/GUARDS.md) |
| Boxes visualizer (Java-free rendering) | [docs/boxes_view.md](docs/boxes_view.md) |
| Language server setup | [docs/LSP.md](docs/LSP.md), [docs/LSP_EDITORS.md](docs/LSP_EDITORS.md) |
| Release history | [CHANGELOG.md](CHANGELOG.md) |

## Conformance

**100% of 123 OMG XPect conformance tests pass** (123/123).

Run the full suite:
```bash
pytest -m conformance
```
