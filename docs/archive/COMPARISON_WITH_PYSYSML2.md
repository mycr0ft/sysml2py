# sysmlpy vs PySysML2: Comparison

A detailed comparison of two Python libraries for SysML v2 textual modeling.

| Feature | sysmlpy | PySysML2 |
|---------|---------|----------|
| **Version** | 0.31.3 | 0.1.1 |
| **Maintainer** | Jon Fox (mycr0ft) | Keith Lucas (DAF Digital Transformation Office) |
| **License** | MIT | Apache 2.0 |
| **Repository** | https://github.com/mycr0ft/sysmlpy | https://github.com/DAF-Digital-Transformation-Office/PySysML2 |
| **Language** | Python 3.9+ | Python 3.8+ |
| **Parser** | ANTLR4 (full SysML v2 grammar) | ANTLR4 (subset grammar) |
| **Stars** | ~250+ | ~60 |
| **Commits** | 1000+ | 2 (initial commit + 1 update) |
| **Core source** | ~37K lines across 11 modules | ~1.5K lines across 4 modules |

---

## 1. Parsing Coverage

### sysmlpy

Full SysML v2 / KerML metamodel via ANTLR4 grammar. 319 grammar classes in `grammar/classes.py` covering all SysML v2 constructs:

**Structural:** packages, parts, items, ports, interfaces, connections, flows (with flow definitions), attributes (with redefinition), enumerations, references, allocations, messages

**Behavioral:** actions (definition usage, shorthand, succession, decomposition), states (with transitions), calculations, constraints

**Control flow:** if/else, while loops, for loops, fork, join, decision, send, accept, terminate

**Requirements & analysis:** requirements, use cases, objectives, analysis cases, verification cases, trade studies

**Views & cross-cutting:** views (general, action flow, interconnection, state transition, package), viewpoints, concerns, metadata, renderings, individuals

**Full round-trip:** all 77 grammar tests pass (parse -> grammar object -> dump() -> re-parse -> identical)

```python
# sysmlpy parsing examples
from sysmlpy import loads, parse, load_grammar

# Parse from string — returns Model
model = loads("""
    package Simple {
        part def Motor;
        part myMotor : Motor;
    }
""")

# Parse with error handling (never raises)
m, errors = parse("invalid syntax {{}")
# returns (None, [error lines])

# Raw dict access
d = load_grammar("part def A;")
```

### PySysML2

Partial SysML v2 grammar with ~15 element types, 4 relationship types:

**Elements:** package, part definition, attribute, comment, doc, import, include, item, objective, port, use case, connection end part

**Relationships:** connect, specializes, redefines, message

**Not implemented (raise `NotImplementedError`):** actor, about

**Not covered at all:** actions, states, constraints, calculations, flows (no flow def), interfaces, requirements, views/viewpoints, control flow, analysis cases, enumerations, references, allocations, messages (partially), metadata, renderings

```python
# PySysML2 parsing examples
from pysysml2.modeling import Model

model = Model()
model.from_sysml2_file("model.sysml2")
# No string-based API; only file-based

# No load_grammar/loads equivalent — must write to file first
# No error handling API
```

---

## 2. Programmatic API

### sysmlpy

Full programmatic construction of SysML models with type checking, unit support, and round-trip text generation:

```python
from sysmlpy import Part, Item, Attribute, Action, Port, Connection, State, \
    Requirement, Case, Constraint, Calculation, Enumeration, ureg

# Structure
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
#         attribute mass = 100 kg;
#     }
#     item lens;
# }

# Behavior
action = Action(definition=True, name='Focus')
action.add_input('scene', 'Scene')
action.add_output('image', 'Image')

# Ports & connections
port1 = Port(name='data')
port2 = Port(name='power')
conn = Connection(name='bus', source=port1, target=port2)

# States
state = State(name='Idle')
state.add_transition('Active', trigger='start')

# Requirements
req = Requirement(name='Performance')
req.add_text('The system shall respond in < 100ms')

# Analysis
case = Case(name='ThermalCase')
constraint = Constraint(name='PowerBudget')
calc = Calculation(name='Sum')

# Typed values with units
mass.set_value(5.0 * ureg.kilogram)
length = Attribute(name='length')
length.set_value(10.0 * ureg.meter)

# Enumeration
status = Enumeration(name='Status', values=['ON', 'OFF', 'STANDBY'])
```

### PySysML2

Minimal programmatic API. Elements are constructed by the parser only — no factory-style `Part(name=...)` construction. Elements carry parsed properties as dict-like attributes:

```python
# PySysML2 — no programmatic construction API
# Elements only exist after parsing a .sysml2 file
model = Model()
model.from_sysml2_file("model.sysml2")

# Traversal via anytree RenderTree
from anytree import RenderTree
for pre, fill, node in RenderTree(model):
    if hasattr(node, 'name'):
        print(f"{pre}{node.name}")

# Element properties (populated by parser)
part = some_node  # from tree
print(part.name)        # str
print(part.sysml2_type) # e.g. 'part'
print(part.idx)         # int index
print(part.keywords)    # list of matched keywords
print(part.value_types) # typing info
print(part.constants)   # constant values
print(part.multiplicity) # multiplicity strings

# No set_value(), add_child(), dump(), etc.
# No unit support (units not modeled)
```

---

## 3. Diagram Generation

### sysmlpy (14 view functions)

```python
# PlantUML generation with 14 view types
from sysmlpy import loads, as_general_view, as_action_flow_view, \
    as_state_transition_view, as_interconnection_view, as_package_view, \
    as_tabular_view, as_data_value_tabular_view, as_relationship_matrix_view

model = loads("""
    package Sys {
        part def Motor;
        part myMotor : Motor;
    }
""")

# General view — full graph
print(as_general_view(model))
# @startuml
# skinparam style strictuml
# ...
# @enduml

# Action flow view — control/object flows
print(as_action_flow_view(model))

# State transition view — hierarchical states
print(as_state_transition_view(model))

# Tabular output in multiple formats
print(as_tabular_view(model, output_format="markdown"))
print(as_tabular_view(model, output_format="html"))

# Relationship matrix
print(as_relationship_matrix_view(model))

# Style options: "bw" (default) or "color"
print(as_general_view(model, style="color"))

# Direction: "left_to_right" or "top_to_bottom"
print(as_general_view(model, direction="left_to_right"))

# Custom PlantUML styling
custom = "skinparam backgroundColor #lightyellow"
print(as_general_view(model, custom_style=custom))
```

### PySysML2 (basic graphviz output)

```python
# Single graphviz dot/png export — not SysML-aware views
model = Model()
model.from_sysml2_file("model.sysml2")

# Export to graphviz DOT
model.to_dot(out_dir="./output")

# Export to PNG (requires graphviz `dot` command)
model.to_png(out_dir="./output")

# What the output shows: a generic anytree node-link diagram
# No SysML-specific view types (no BDD, IBD, parametric, etc.)
# No PlantUML support
# No tabular/matrix views
# No style customization
```

---

## 4. Semantic Analysis

### sysmlpy

```python
from sysmlpy import loads, analyze

model = loads("""
    package Test {
        part def Motor;
        part myMotor : Motor;
    }
""")

result = analyze(model)

# Check for errors
if result.errors:
    for issue in result.errors:
        print(f"[{issue.severity}] {issue.code}: {issue.message}")
        print(f"  Element: {issue.element}")

# Raise on errors
result.raise_on_errors()  # ValueError if any errors found

# Check severity
print(result.errors)    # filter error-severity
print(result.warnings)  # filter warning-severity
print(bool(result))     # True if no errors (warnings OK)
```

**9 OCL well-formedness checks:**

| Code | Rule |
|------|------|
| `DUPLICATE_NAME` | No duplicate names in scope |
| `CYCLIC_SPECIALIZATION` | No cyclic specialization |
| `INCOMPATIBLE_SUBSETTING` | Subsetting references defined feature |
| `INCOMPATIBLE_REDEFINITION` | Redefinition references defined feature |
| `INCOMPATIBLE_PART_DEFINITION` | Part usage typed by PartDefinition |
| `INCOMPATIBLE_PORT_DEFINITION` | Port usage typed by PortDefinition |
| `INCOMPATIBLE_FEATURE_CHAIN` | Chained features compatible types |
| `INVALID_MULTIPLICITY_BOUNDS` | Lower <= upper bound |
| `UNRESOLVED_IMPORT` | Import target exists |

**Import resolution:** 5 patterns (private `*`, specific name, recursive `::*::**`, public, protected), hierarchical scope resolution, qualified name lookup (`P::A`).

**Library symbol index:** scans 88 bundled `.kerml`/`.sysml` library files (~1,417 symbols).

```python
# Semantic analysis with import resolution
from sysmlpy import load_with_dependencies

model, _ = load_with_dependencies("main.sysml", search_paths=["./libraries"])
result = analyze(model)

# Symbol table access
from sysmlpy import SemanticAnalyzer
analyzer = SemanticAnalyzer(model)
scope = analyzer.current_scope
for name, symbol in scope.symbols.items():
    print(f"{name}: {symbol}")
```

### PySysML2

No semantic analysis module. No validation, no OCL checks, no symbol resolution, no import resolution beyond recording the `import` element in the tree.

```python
# PySysML2 — no analyze() equivalent
# The parser records imports as elements but does not resolve them
```

---

## 5. Storage Backends

### sysmlpy

```python
from sysmlpy import InMemoryStore, NetworkXStore, KuzuStore, CayleyStore, \
    create_store

# Abstract Store protocol with 4 implementations

# In-memory (stdlib, no deps)
store = InMemoryStore()
store.put("part1", {"name": "Motor", "type": "Part"})
store.put("part2", {"name": "Sensor", "type": "Part"})
store.put_edge("part1", "connects", "part2")

# Get/query
print(store.get("part1"))
print(store.query("type", "Part"))
print(store.neighbors("part1", "connects"))

# NetworkX graph analysis
store = NetworkXStore()
# ... populate ...
store.connected_components()
store.centrality()
store.cycles()
store.stats()
store.export_graphml()

# KuzuDB (embedded, persistent, Cypher queries)
store = KuzuStore(database_path="./my_model.kuzu")

# Cayley (remote graph DB via HTTP)
store = CayleyStore(base_url="http://localhost:64210")

# Factory
store = create_store("memory")
store = create_store("networkx")

# Graph traversal
store.descendants("part1")
store.ancestors("part1")
store.path("part1", "part5")
```

### PySysML2

No storage abstraction. Models live in memory as anytree `NodeMixin` trees. No persistence, no graph DB integration, no query language support.

```python
# PySysML2 — only in-memory anytree trees
# Export via to_JSON(), to_csv(), to_excel() — file-based serialization only
model.to_JSON("./output.json")    # anytree JSON export
model.to_csv("./output.csv")      # pandas DataFrame export
model.to_excel("./output.xlsx")   # Excel via openpyxl
```

---

## 6. Output Formats

| Format | sysmlpy | PySysML2 |
|--------|---------|----------|
| SysML v2 text (`dump()`) | Yes (full round-trip) | No |
| PlantUML | Yes (14 view types) | No |
| Graphviz DOT | No (uses PlantUML) | Yes (basic tree) |
| PNG | Via PlantUML renderer | Via graphviz |
| JSON | Yes (`get_definition()`) | Yes (anytree) |
| CSV | Via pandas export | Yes (via anytree->DataFrame) |
| Excel | Via pandas export | Yes (via openpyxl) |
| Markdown tables | Yes (GridView output) | No |
| HTML tables | Yes (GridView output) | No |
| Python `repr()` | Yes | No |
| In-place formatting | Yes (`--in-place` CLI flag) | No |

---

## 7. CLI

### sysmlpy

```bash
# Format/analyze SysML files from command line
sysmlpy model.sysml2                  # Print model repr
sysmlpy model.sysml2 --dump           # Print SysML text
sysmlpy model.sysml2 --json           # Print JSON/dict
sysmlpy model.sysml2 --python         # Print Python repr
sysmlpy model.sysml2 -i               # Format in-place
sysmlpy model.sysml2 --check          # Check formatting, exit 1 if unformatted
sysmlpy model.sysml2 -l ./libraries   # Use library path
```

### PySysML2

```bash
# Export model to various data formats
pysysml2 export model.sysml2 --format json,txt,csv,xlsx,dot,png
```

---

## 8. Test Suite

| Metric | sysmlpy | PySysML2 |
|--------|---------|----------|
| **Total tests** | 545+ | ~14 |
| **Test files** | 14 | 2 |
| **Grammar round-trip** | 77 (100% pass) | 0 |
| **Public API** | 54 | 0 |
| **PlantUML views** | 108 | 0 |
| **Semantic analysis** | 107 | 0 |
| **Navigation** | 33 | 0 |
| **Validator (ISQ)** | 34 | 0 |
| **Storage backends** | 46 | 0 |
| **Conformance (OMG)** | 123 (100% pass) | 0 |
| **Project loading** | 14 | 0 |
| **Imports** | 16 | 0 |
| **Model serialization** | — | ~14 |

---

## 9. Standard Library

### sysmlpy

Bundles **88 library files** (`.kerml` + `.sysml`) across kernel, systems, and domain packages:

- **kernel/ (36 files):** Base, ScalarValues, Collections, Functions (Boolean, Integer, Real, String, Trig, Vector), Occurrences, Performances, Transfers, Clocks, Links, Controls, SpatialFrames
- **systems/ (21 files):** Actions, Allocations, AnalysisCases, Attributes, Calculations, Cases, Connections, Constraints, Flows, Interfaces, Items, Metadata, Parts, Ports, Requirements, StandardViewDefinitions, States, SysML, UseCases, VerificationCases, Views
- **domain/ (30+ files):** Analysis, CauseEffect, Geometry, Metadata, QuantitiesUnits, RequirementDerivation

All 88 files indexed (~1,417 symbols) for import resolution.

### PySysML2

No bundled standard library. No library symbol indexing.

---

## 10. Unit Validation

### sysmlpy

```python
from sysmlpy import loads
from sysmlpy.validator import validate_unit_conformance

model = loads("""
    package Test {
        part def Sensor {
            attribute mass : MassValue;
        }
        part mySensor : Sensor {
            attribute mass = 100 kg;
        }
    }
""")

issues = validate_unit_conformance(model)
# Checks pint unit dimensions against 300+ ISQ type mappings
# Reports mismatches like "Expected dimension [mass], got [length]"
```

300+ ISQ type-to-dimension mappings across base quantities, space & time, mechanics, electromagnetism, thermodynamics, photometry. 21 US Customary unit definitions (inch, foot, psi, horsepower, BTU, gallon, etc.).

**Known issue:** `antlr_visitor.py` hardcodes `specialization=None` for top-level attributes, so unit validation may miss some type information at the top level.

### PySysML2

No ISQ validation, no unit system, no dimensional analysis.

---

## 11. Multi-file Project Support

### sysmlpy

```python
from sysmlpy import load_files, load_project, load_with_dependencies

# Load specific files (same-named packages merge)
model = load_files(["a.sysml", "b.sysml"])

# Load all .sysml/.kerml in a directory
model = load_project("./models")

# Auto-resolve imports from search paths
model, _ = load_with_dependencies("main.sysml", search_paths=["./libs", "./components"])
```

### PySysML2

Single-file loading only. No project resolution.

---

## 12. Model Navigation

### sysmlpy

```python
from sysmlpy import loads

model = loads("""
    package Sys {
        part def Motor;
        part sensor : Sensor;
        part myMotor : Motor {
            attribute power : Real;
        }
    }
""")

# Typed accessors
print(model.parts)       # [Part('sensor'), Part('myMotor')]
print(model.attributes)  # [Attribute('power')]
print(model.packages)    # [Package('Sys')]

# Searchable mixin
model.find("Motor")                       # by name (recursive)
model.find(sysml_type="Part")             # by type
model.find(name="sensor", recursive=True)
model.find_one("Motor")                   # raises if 0 or >1

model.all("Part")       # shortcut for find(sysml_type="Part")
model.all("Attribute")

# Container protocol
len(model)              # number of direct children
"Motor" in model        # name containment check
for child in model:     # iterate over children
    print(child)

# String representation
str(model)              # SysML text

# Dictionary round-trip
model.get_definition()  # dict form
```

### PySysML2

```python
# Only anytree RenderTree traversal
from anytree import RenderTree

for pre, fill, node in RenderTree(model):
    if isinstance(node, Element):
        print(f"{pre}[{node.idx}] {node.name}")

# No typed accessors (no model.parts, model.attributes, etc.)
# No find/find_one/all search
# No container protocol (len, in, iteration not on Model)
# No dump()/get_definition() round-trip
```

---

## Summary

| Capability | sysmlpy | PySysML2 |
|------------|---------|----------|
| Full SysML v2 grammar coverage | ✓ (319 classes) | ✗ (~15 elements) |
| Round-trip text output | ✓ `dump()` → parseable SysML | ✗ |
| Programmatic model construction | ✓ 30+ public API classes | ✗ No factory API |
| Type relationships | ✓ (set_type, typing) | ✗ |
| Unit system (pint ISQ) | ✓ 300+ mappings | ✗ |
| Unit validation | ✓ dimensional analysis | ✗ |
| PlantUML diagrams | ✓ 14 view types | ✗ |
| Graphviz output | ✗ (uses PlantUML) | ✓ basic DOT/PNG |
| Semantic analysis | ✓ 9 OCL checks | ✗ |
| Symbol resolution | ✓ hierarchical + libraries | ✗ |
| Import resolution | ✓ 5 patterns | ✗ (records imports only) |
| Storage backends | ✓ 4 (memory/networkx/kuzu/cayley) | ✗ (in-memory only) |
| Standard library | ✓ 88 bundled files | ✗ |
| Multi-file projects | ✓ load_files/project/dependencies | ✗ single file |
| Model navigation/search | ✓ Searchable mixin, 29 typed accessors | ✗ anytree RenderTree only |
| CLI | ✓ format/check/dump/python/in-place | ✓ export (6 formats) |
| CSV/Excel/JSON export | ✓ via pandas | ✓ |
| Control flow grammar | ✓ if/while/for/fork/join/decision/send/accept/terminate | ✗ |
| Requirements | ✓ Requirement, UseCase | ✗ partial use case |
| States | ✓ State with transitions | ✗ |
| Actions | ✓ Action with I/O | ✗ |
| Constraints | ✓ Constraint | ✗ |
| Calculations | ✓ Calculation | ✗ |
| Interfaces | ✓ Interface | ✗ |
| Flow connections | ✓ Flow, FlowDef | ✗ |
| Allocations | ✓ Allocation | ✗ |
| Views/Viewpoints | ✓ View, Viewpoint, Concern | ✗ |
| Analysis cases | ✓ Case, AnalysisCase, VerificationCase | ✗ |
| Enumerations | ✓ Enumeration | ✗ |
| Message passing | ✓ Message | ✓ (partial) |
| ISQ library files | ✓ 88 indexed files | ✗ |
| OMG conformance tests | ✓ 123/123 pass | ✗ |
| Test suite size | 545+ tests | ~14 tests |
| Maturity | Active development (v0.31) | Early prototype (v0.1) |

---

## Verdict

**sysmlpy** provides comprehensive, production-grade SysML v2 support with full grammar coverage, programmatic model construction, semantic analysis, 14 PlantUML view types, 4 storage backends, ISQ unit validation, multi-file project support, and a complete standard library. It supports round-trip text output (`dump()`) from all grammar objects.

**PySysML2** is a lightweight early-prototype focused on data-science-oriented model export (CSV, Excel, JSON, graphviz). It parses a subset of SysML v2 (~15 element types) into an anytree hierarchy and can export to pandas-friendly formats. It has no semantic analysis, no programmatic construction API, no round-trip text output, no unit validation, and no diagram generation beyond basic anytree graphviz trees.

**Choose sysmlpy if you need:** full SysML v2 modeling, diagram generation, semantic validation, multi-file projects, or programmatic model construction.

**Choose PySysML2 if you need:** a lightweight parse-to-DataFrame pipeline for simple SysML models with basic element types, and do not need round-trip, validation, diagrams, or behavioral elements.

---

*Comparison generated 2026-06-06 based on sysmlpy v0.31.3 and PySysML2 v0.1.1.*
