# sysmlpy — Project Status

Current version: **v0.47.0** (2026-08-26)

---

## Completed

### Public API Classes

These classes are fully implemented, have programmatic construction, `dump()` serialization, and test coverage.

| Class | SysML Keyword(s) | Notes |
|---|---|---|
| `Package` | `package` | Name, shortname, children, `load_from_grammar` |
| `Model` | *(root)* | Wraps packages; load from string |
| `Part` | `part` / `part def` | Typed by, children, `load_from_grammar` |
| `Item` | `item` / `item def` | Typed by, children |
| `Attribute` | `attribute` / `attribute def` | `set_value`/`get_value` with `pint` units |
| `Port` | `port` / `port def` | In/out/inout directed features, add attribute |
| `Action` | `action` / `action def` | Add in/out parameters, typed by, specializes |
| `Reference` | `ref` | Simple, typed, and redefinition (`ref :>> name : Type;`) |
| `Requirement` | `requirement def` / `requirement` | Subject, actor, doc, constraint, assume constraint |
| `UseCase` | `use case def` / `use case` | Subject, actor, include |
| `Interface` | `interface def` / `interface` | Add end, add connection |
| `Message` | `message` | From, to, of-type |
| `State` | `state def` / `state` | Transitions, entry/do/exit actions, `.parent` property |
| `Transition` | `transition` | Source, target, guard, trigger, effect |
| `Constraint` | `constraint def` / `constraint` | Assert constraint, derivation forms |
| `AnalysisCase` | `analysis def` / `analysis` | Subject, objective, result expression |
| `VerificationCase` | `verification def` / `verification` | Parse and load from grammar |
| `Concern` | `concern def` / `concern` | Parse and load from grammar |
| `View` | `view def` / `view` | Parse and load from grammar |
| `Viewpoint` | `viewpoint def` / `viewpoint` | Parse and load from grammar |
| `Individual` | `individual def` / `individual` | Parse and load from grammar |
| `Metadata` | `metadata def` / `metadata` | Parse and load from grammar |
| `Rendering` | `rendering def` / `rendering` | Parse and load from grammar |
| `Allocation` | `allocation def` / `allocation` | Parse and load from grammar |
| `Flow` | `flow def` / `flow` | Parse and load from grammar |
| `Connection` | `connection def` / `connection` | Parse and load from grammar |
| `Calculation` | `calc def` / `calc` | Parse and load from grammar |
| `Enumeration` | `enum def` / `enum` | Parse and load from grammar |

### Relationship Methods (on all Usage/Definition classes)

| Method | Syntax |
|---|---|
| `set_typed_by()` | `: TypeName` |
| `set_specializes()` | `:> SuperDef` (definitions) |
| `set_subsets()` | `:> superset` (usages) |
| `set_redefines()` | `:>> original` |
| `add_child()` | fluent child builder |

### Parser

- **ANTLR4 parser** — default parser, using OMG grammar v2026.03.0
  - `load()`, `loads()`, `parse()`, `load_grammar()` (public API)
  - `load_antlr()`, `load_grammar_antlr()` (explicit ANTLR4 path)
  - Full ANTLR4 visitor (`antlr_visitor.py`, ~11K lines) converting parse tree to internal dict representation
  - Supports comments, documentation blocks, and annotating elements
  - Supports Case, AnalysisCase, VerificationCase, and TradeStudy definitions
  - State machine support: entry/do/exit actions, accept/send/perform/assign nodes, transitions with guards
  - Non-raising `parse(text)` variant: returns `(Model, [])` on success, `(None, [errors])` on syntax error

### Grammar Round-Trip Coverage (parse → dump)

**97 / 97 tests passing (100%)** as of v0.40.0.

The suite grew from 79 to 96 cases (full-model round-trips drawn from the
OMG spec corpus, including ActionTest / ControlNodeTest / DecisionTest
action-body successions). v0.37.0 additionally fixed corpus-level load
crashes: implicit-package wrap vs trailing line comments, MetadataFeature /
TextualRepresentation annotating elements, missing succession-member
classes, WHEN triggers, and malformed interface ends.

All categories pass, including the 14 control flow node tests (IfNode,
WhileLoopNode, ForLoopNode, ControlNode, SendNode, AcceptNode, TerminateNode).

| Category | Pass | Total |
|---|---|---|
| Packages | 3 | 3 |
| Part definitions | 1 | 1 |
| Generalization / Subsetting / Redefinition | 3 | 3 |
| Enumerations | 2 | 2 |
| Parts | 2 | 2 |
| Items | 1 | 1 |
| Connections | 1 | 1 |
| Ports | 2 | 2 |
| Interfaces | 2 | 2 |
| Binding connectors | 2 | 2 |
| Flow connections | 3 | 3 |
| Actions | 5 | 5 |
| States | 6 | 6 |
| Expressions | 4 | 4 |
| Calculations | 3 | 3 |
| Constraints | 7 | 7 |
| Requirements | 4 | 4 |
| Analysis | 3 | 3 |
| Control flow | 14 | 14 |
| Lifecycle metadata | 9 | 9 |
| Corpus-driven full models | +17 | +17 |
| **Total** | **96** | **96** | |

### Grammar Resilience (v0.27.0)

All 68+ `raise NotImplementedError` stubs in `grammar/classes.py` replaced with
graceful handling. The parser no longer crashes on any edge-case input.

**Stubs fully implemented** (`__init__`, `dump()`, `get_definition()`):
- `PortionKind` — stores `kind` field (snapshot/timeslice/individual)
- `PrefixMetadataMember` — stores `memberElement`, dumps as `@<name>`
- `LifeClassMembership` — stores `memberElement`, dumps as `lifeClass <name>`

**Missing classes added:**
- `DefinitionBody`, `DefinitionBodyItem`
- `FeatureSpecializationPart`, `SubclassificationPart`

**Catch-all unknown branches** → print warning instead of crashing (68 sites):
- `DefinitionElement`, `InterfaceBodyItem`, `OccurrenceUsageElement`,
  `NonOccurrenceUsageElement`, `PrimaryExpression`, `PackageBody`,
  `RelationshipBody`, `ConnectorPart`, `FeatureSpecialization`, and more.

**Expression chain classes** — gracefully handle `None` child / non-empty operands:
- `ConditionalExpression`, `NullCoalescingExpression`, `ImpliesExpression`,
  `OrExpression`, `XorExpression`, `ClassificationExpression`,
  `ExponentiationExpression`, `UnaryExpression`, `ExtentExpression`

### Semantic Analysis Engine (v0.17.0 → v0.20.0)

| Feature | Status | Details |
|---|---|---|
| Symbol table | ✅ Complete | Hierarchical scopes with parent chain lookup |
| Import resolution | ✅ Complete | Namespace (`::*`), membership, recursive (`::*::**`) |
| Import visibility | ✅ Complete | `private`/`public`/`protected` enforcement |
| Library symbol index | ✅ Complete | 88 `.kerml`/`.sysml` files, ~1,417 symbols |
| Inheritance resolution | ✅ Complete | Supertype chain traversal for subsetting/redefinition |
| OCL constraints | ✅ 8 checks | See table below |

#### Implemented OCL Well-Formness Checks

| Code | Rule | Description |
|------|------|-------------|
| `UNDEFINED_SYMBOL` | — | Reference to non-existent type or feature |
| `DUPLICATE_NAME` | Namespace.duplicate_names | Two members with same name in a scope |
| `CYCLIC_SPECIALIZATION` | Type.no_cyclic_specialization | Type specializing itself (directly or indirectly) |
| `INCOMPATIBLE_SUBSETTING` | Feature.subsetting_compatible | Subsetting ref to undefined feature |
| `INCOMPATIBLE_REDEFINITION` | Feature.redefinition_compatible | Redefinition ref to undefined feature |
| `INCOMPATIBLE_PART_DEFINITION` | Part.definition_compatible | Part typed by non-PartDefinition |
| `INCOMPATIBLE_PORT_DEFINITION` | Port.definition_compatible | Port typed by non-PortDefinition |
| `INCOMPATIBLE_FEATURE_CHAIN` | Feature.chaining_compatible | Chained features with incompatible types |
| `INVALID_MULTIPLICITY_BOUNDS` | Multiplicity.bounds_valid | Lower bound > upper bound |
| `UNRESOLVED_IMPORT` | — | Import target does not exist |

### PlantUML View Generation (v0.25.2 → v0.27.0)

| Function | SysML v2 View | Output | Notes |
|---|---|---|---|
| `as_general_view()` | General View (GV) | PlantUML | All element types, full filtering |
| `as_package_view()` | Package View | PlantUML | Package structure + import arrows |
| `as_action_flow_view()` | ActionFlowView (AFV) | PlantUML | Actions + flow connections |
| `as_interconnection_view()` | InterconnectionView (IV) | PlantUML | Parts, ports, connections |
| `as_state_transition_view()` | StateTransitionView (STV) | PlantUML | States + transitions |
| `as_tabular_view()` | Tabular View (GridView) | PlantUML / MD / HTML | Configurable columns |
| `as_data_value_tabular_view()` | Data Value Tabular View | PlantUML / MD / HTML | Attribute values + units |
| `as_relationship_matrix_view()` | Relationship Matrix View | PlantUML / MD / HTML | Cross-element relationship matrix |

All views support: `focus`, `elements`, `show_external`, `direction`, B&W/color toggle, `custom_style`, and legend.

### Nested Requirement Children (v0.36.1)

`Requirement.load_from_grammar` now populates `self.children` with nested `requirement` usages and `requirement def` definitions encountered in the body. Previously the body walk stubbed out `DefinitionBodyItem` with `pass`, so nested requirements were parsed by the grammar but dropped from the public object tree. Deep nesting recurses; `.parent` links are set on each child. Non-requirement nested elements are skipped for now. Grammar-object round-trip is unaffected.

### Boxes-backed State-Machine Visualizer (v0.36.0)

Optional renderer that produces a [`boxes`](https://github.com/mycr0ft/boxes) Diagram with native UML state shapes (rounded `«state»` boxes, filled-circle initial pseudostate, bullseye final state, orthogonal port-to-port routing). Alternative to `as_state_transition_view()` when you don't want a PlantUML/Java runtime.

| Function | Returns | Notes |
|---|---|---|
| `as_state_transition_view_boxes(model, focus=None)` | `boxes.Diagram` | Build an in-memory diagram you can introspect / extend |
| `render_state_transition_view(model, focus=None, routing=...)` | braille terminal string | Quick terminal preview |
| `render_state_transition_view_svg(model, focus=..., routing=..., scale=...)` | SVG string | Vector output for embedding in docs |

Handles `entry; then X;`, `do`/`exit` actions as state attributes, guarded transitions (`if guard`), shorthand `accept X then Y;`, the reserved `done` final-state target, dotted feature-chain targets (`S2.S3`), nested composite states, and `parallel` region composition. Lazy-loaded so `import sysmlpy` works without `boxes` installed. See [`docs/boxes_view.md`](boxes_view.md) for the full pseudostate landscape and worked examples.

### Storage Backends

| Backend | Dependencies | Persistence | Use Case |
|---------|-------------|-------------|----------|
| `InMemoryStore` | None | Volatile | Testing, small models |
| `NetworkXStore` | networkx | Volatile | Graph analysis, centrality, cycles |
| `KuzuStore` | kuzu | Disk (optional) | Embedded graph DB, Cypher queries |
| `CayleyStore` | requests | Server-managed | Remote graph DB, multi-tenant |

### Test Coverage

| Test file | Tests | Status |
|---|---|---|
| `tests/grammar_test.py` | 97 | ✅ All pass (100%) |
| `tests/redefined_name_test.py` | 8 | ✅ All pass (100%) |
| `tests/class_test.py` | 54 | ✅ All pass |
| `tests/main_test.py` | 7 | ✅ All pass |
| `tests/plantuml_test.py` | 108 | ✅ All pass |
| `tests/semantic_test.py` | 118 | ✅ All pass |
| `tests/navigate_test.py` | 33 | ✅ All pass |
| `tests/import_test.py` | 16 | ✅ All pass |
| `tests/validator_test.py` | 34 | ✅ All pass |
| `tests/project_test.py` | 17 | ✅ All pass |
| `tests/store_test.py` | 46 | Pass (optional deps skipped if not installed) |
| `tests/conformance_test.py` | 123 | ✅ All pass (100%) |
| **Total** | **635** | **635 pass** |

### Documentation

- `README.md` — installation, usage examples, view rendering docs
- `AGENTS.md` — AI agent onboarding guide
- `docs/index.md` — project overview
- `docs/quickstart.md` — step-by-step usage guide
- `TUTORIAL.md` — comprehensive guide with class mapping tables
- `docs/PROJECT_SUMMARY.md` — work summary for future agents/team members
- `docs/plantuml-reference-analysis.md` — PlantUML generator assessment
- `docs/plantuml-examples/` — rendered diagram examples

---

## Completed Since v0.27.0

### Action Control-Flow Node Classes (v0.28.0–v0.29.0)

All 14 control flow grammar classes are now ported to `grammar/classes.py`:

- `IfNode`, `WhileLoopNode`, `ForLoopNode`, `ControlNode`, `InitialNode`,
  `InitialNodeMember`, `SendNode`, `AcceptNode`, `TerminateNode`,
  `ActionTargetSuccession`, `ActionTargetSuccessionMember`,
  `GuardedSuccession`, `GuardedSuccessionMember`,
  `SourceSuccession`, `SourceSuccessionMember`

### Mutation API Stabilization (v0.30.2)

All private underscore-prefixed mutation methods given public aliases:
- `_set_child()` → `add_child()`; `_set_name()` → `set_name()`; `_set_typed_by()` → `set_typed_by()`
- `_set_specializes()` → `set_specializes()`; `_set_subsets()` → `set_subsets()`
- `_set_redefines()` → `set_redefines()`; `_get_child()` → `get_child()`
- Private names kept as backward-compatible aliases.

### Model Navigation Enhancements (v0.30.2–v0.31.0)

- `find_one()` — single-match find with `LookupError` on ambiguity
- `__iter__`, `__len__`, `__contains__` — container protocol on all model elements
- `__str__` — returns SysML text (delegates to `dump()`)
- `find()` uses `sysml_type=` keyword (legacy `type=` still works with deprecation)
- Typed property accessors (`model.parts`, `model.actions`, etc.)

### Semantic Analysis Enhancements (v0.30.2)

- `AnalysisResult` class with `.errors`, `.warnings`, `.raise_on_errors()`, `bool()`
- `analyze(model, strict=True)` raises immediately on errors
- `SysMLSyntaxError` exported from package root
- Non-raising `parse()` variant: `model, errors = parse(text)`

### Jupyter Integration (v0.30.2)

- `_repr_html_()` on all model elements — collapsible HTML tree in notebooks

### Grammar Round-Trip (v0.31.0)

- All 97 grammar tests pass (100%) — control flow, successions, lifecycle metadata complete. New tests/redefined_name_test.py (8 tests) for re-declaration name resolution and `References` (`:>`, `references`) handling.
- No deferred tests remaining

---

## Known Issues

| Location | Description |
|---|---|
| `grammar/classes.py` | `PackageBodyElement` name is hardcoded; `#!TODO This isn't always the case` |
| `definition.py` (`RootNamespace`) | `load_package_body()` raises `NotImplementedError` for `AliasMember` and `Import` nodes |
| `antlr_visitor.py` ~line 9558 | Top-level attribute multiplicity not captured (nested attributes work) |
| `definition.py` | Dead code — duplicate `elif inner_class == "ActionUsage"` block |
| `usage.py` | Type relationships (`: TypeName`) not preserved in `load_from_grammar()` |
| `semantic.py` | Names inside constraint bodies (`assert constraint { ... }`) and other expressions are not resolved. A parse-clean result means *parsed*, not *checked* ([issue #3](https://github.com/mycr0ft/sysmlpy/issues/3), finding 4). |

---

## Remaining Work

### High Priority

| Feature | Description |
|---|---|
| Typed-by preservation | Type relationships not preserved when loading elements from grammar (`usage.py`, marked `#!TODO Typed By`) |
| Fix top-level attribute multiplicity | Visitor hardcodes `specialization=None` for top-level attributes |
| AliasMember / Import handling | `definition.py` `load_package_body()` needs these node types |

### Medium Priority

| Feature | Description |
|---|---|
| Connection multiplicity ends | `connect X[0..1] to Y[1]` multiplicity in connector ends |
| Nested `:>>` redefines in return | `return attribute X : Type { :>> feature = expr; }` |
| Feature chain type resolution | Full chain resolution (`a.b.c`) in `semantic.py` |
| Connector end compatibility | Full type-assignability check in `_check_connector_ends_compatible()` |

### Low Priority

| Feature | Description |
|---|---|
| Grammar auto-update pipeline | Automated refresh from the OMG KEBNF spec when new releases drop |
| Full OCL constraint library | Machine-readable OCL constraints extendable without code changes |
| Parse library files (not regex) | Replace `LibrarySymbolIndex._extract_from_file()` with actual parsing |

---

## Conformance Test Suite

Source: **SysML-v2-Pilot-Implementation-2026-03** (`org.omg.sysml.xpect.tests`)
Library: **88 files** bundled at `src/sysmlpy/library/` (kernel/ systems/ domain/)
Test files: **123 `.sysml` files** under `tests/sysmlv2/`, each with a `.error` sidecar

Run with: `poetry run pytest -m conformance`

### Current results (2026-05-27)

**123 / 123 passing (100%)**

| Category | Files | Pass | Fail | Pass % |
|---|---|---|---|---|
| `simpletests/` | 37 | 37 | 0 | 100% |
| `validation/valid/` | 34 | 34 | 0 | 100% |
| `validation/invalid/` | 47 | 47 | 0 | 100% |
| `expression/` | 4 | 4 | 0 | 100% |
| `linking/` | 1 | 1 | 0 | 100% |
| **Total** | **123** | **123** | **0** | **100%** |

---

## Summary Counts

| Category | Count |
|---|---|---|
| Public API classes (complete) | 28 |
| Grammar classes with `get_definition()` | ~260+ of 319 |
| Grammar classes with graceful fallback | All 319 (no more NotImplementedError crashes) |
| Unit + grammar + integration tests | 635 passing |
| Grammar round-trip tests passing | **97 / 97 (100%)** |
| Helper-property tests | 8 / 8 |
| Grammar-side References dispatch | ✅ | | |
| PlantUML rendering tests | **108 passing** |
| Conformance tests (2026-03 XPect suite) | **123 / 123 (100%)** |
| Semantic analysis tests | **118 passing** |
| Storage backend tests | **46 passing** (optional deps skipped if missing) |
| Bundled standard library files | 88 (kernel `.kerml` + systems `.sysml` + domain `.sysml`) |
| Library symbols indexed | ~1,417 |
| PlantUML view functions | 10 (GV, PV, AFV, IV, STV, SV, CV, Tabular, DataValue, RelMatrix) |
