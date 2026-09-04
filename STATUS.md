# sysmlpy — Project Status

Current version: **v0.68.0** (2026-09-03)

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

- **CLI** — `sysmlpy` console script with subcommands (v0.61.0):
  `parse` (repr/dump/grammar-JSON), `analyze` (semantic analysis with
  CI exit codes: 0 clean, 1 findings at `--fail-on` threshold, 2 parse
  error; text or `--format json`), `view --view NAME` (all 11 views,
  `--focus`, `--element`, `--style`, `--direction`, `--format`, `-o`),
  `format` (alias `fmt`, multiple files), `trace` (requirement
  traceability & verification coverage: `--format text|markdown|json`,
  `--fail-on uncovered`, `-o`; exit 0 clean, 1 uncovered, 2 parse error).
  Legacy flat invocation (`sysmlpy FILE --dump`) preserved with original
  exit codes.
- **Requirement traceability** — `sysmlpy.traceability`
  (`extract_traceability()` → `TraceabilityReport` with per-requirement
  traces, coverage queries, text/markdown/JSON output;
  `as_traceability_matrix_view()` in markdown/html/plantuml). Satisfy /
  verify / verification / subject relationships parse and round-trip
  (v0.62.0).
- **JSON interchange** — `sysmlpy.interchange` (`to_interchange()` /
  `from_interchange()`): JSON-LD-style partition documents (flat
  ``@graph``, ``@id``/``@type`` elements, deterministic uuid5 ids) with
  lossless import back to a live model (v0.63.0).
- **Expression evaluator** — `sysmlpy.evaluator`
  (`collect_values()` / `evaluate_expression()` /
  `evaluate_calculation()` / `check_constraints()`): pint-bound
  evaluation of attribute defaults, calc results and constraint bodies,
  with what-if bindings; `sysmlpy eval` CLI (v0.64.0).
- **LSP server** — `sysmlpy.lsp`: dependency-free LSP 3.17 subset
  (diagnostics, documentSymbol, hover, definition, completion; FULL
  text sync) over stdio; `sysmlpy-lsp` console script + `python -m
  sysmlpy.lsp`; VS Code extension scaffold in `editors/vscode/`;
  Neovim recipes in `docs/LSP.md` (v0.65.0).
- **Spreadsheet bridge** — `sysmlpy.spreadsheet`: CSV export of the
  tabular views (`--format csv`), XLSX workbook export (`sysmlpy xlsx`,
  optional openpyxl extra), and spreadsheet value import into
  evaluator bindings (`eval --set-file`, `import_values_csv()`)
  (v0.66.0).
- **Official SysML v2 notation fidelity** — edge encodings aligned to
  the OMG pilot's PlantUML generator (thick plain connection lines,
  heaviest binding lines, distinct redefinition arrow, send/accept
  action edges, variant/objective/metadata edges); connection
  endpoints now parse (was a parse stub); stv renders composite
  states as nested blocks; gv renders connector edges (v0.67.0).
- **Boxes-backed interconnection + action flow views** —
  `as_interconnection_view_boxes()` (parts as boxes with boundary
  ports, `connection` usages as port-to-port Z-routed edges) and
  `as_action_flow_view_boxes()` (actions as boxes, parameters as
  in/out ports, flows as port-to-port edges, nested actions as
  composite children, successions as dashed `..>` edges) against
  `diagramboxes` (renamed from `boxes`, its v0.4.0); braille + SVG
  render helpers for both (v0.68.0). Control nodes render in both:
  PlantUML afv uses hexagons (deployment syntax has no diamond), boxes
  afv uses true decision diamonds + start/done dots via diagramboxes
  0.5.0, whose sugiyama port routing is obstacle-aware (v0.68.0+).
  The PlantUML interconnection view follows official iv notation
  (enclosure nesting, typed labels, flows/connections as the only
  edges — flows port-to-port; v0.68.0+), and the package view follows
  official package notation: `package "Name" { members }` enclosure,
  leaf definition boxes, typed member labels (v0.68.0+).
  **State-machine simulation** (v0.69.0): `sysmlpy sim FILE` runs a
  `state def` machine Cameo-style — triggers fire transitions, guards
  evaluate against model attribute values (pint-aware) with
  `--set`/`set_value` what-if overrides, completion transitions run to
  completion, effects are logged, and an interactive TUI shows the live
  state with the transitions available from it (`--run "T1; T2"`
  scripts sessions).  Guards also appear in boxes-view edge labels
  (the shorthand-`when` extraction fix); transition `do` effects parse
  through to the simulator — references round-trip, send/assignment
  declarations surface as text (`send Alert to logger`, `x := 5`) —
  and composite regions simulate with qualified names: entering a
  composite lands in its initial substate, region transitions run
  inside it, and composite-level transitions apply from every
  substate.  For color-vision accessibility,
  `set_stereotype_palette("okabe-ito")` switches the `style="color"`
  views to the Okabe-Ito palette (`bw` remains the default).
- **Relationship legends opt-in** — `include_legend=False` by
  default everywhere; the built-in legends restated standard
  notation and are noise. Monochrome `bw` remains the default style
  for color-vision accessibility (v0.68.0).
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
| `tests/grammar_test.py` | 143 | ✅ All pass (100%) |
| `tests/semantic_test.py` | 170 | ✅ All pass |
| `tests/plantuml_test.py` | 131 | ✅ All pass (incl. official-notation tests) |
| `tests/store_test.py` | 97 | Pass (optional deps skipped if not installed) |
| `tests/class_test.py` | 75 | ✅ All pass |
| `tests/traceability_test.py` | 46 | ✅ All pass |
| `tests/interchange_test.py` | 38 | ✅ All pass |
| `tests/evaluator_test.py` | 44 | ✅ All pass |
| `tests/lsp_test.py` | 37 | ✅ All pass |
| `tests/spreadsheet_test.py` | 37 | ✅ 35 pass, 2 skip (no openpyxl) |
| `tests/navigate_test.py` | 42 | ✅ All pass |
| `tests/cli_test.py` | 39 | ✅ All pass |
| `tests/validator_test.py` | 34 | ✅ All pass |
| `tests/repr_test.py` | 34 | ✅ All pass |
| `tests/kuzu_store_test.py` | 32 | Pass (skipped if kuzu not installed) |
| `tests/import_test.py` | 31 | ✅ All pass |
| `tests/cayley_store_test.py` | 22 | Pass (skipped if cayley not installed) |
| `tests/boxes_view_test.py` | 48 | Pass (skipped if diagramboxes not installed) |
| `tests/project_test.py` | 17 | ✅ All pass |
| `tests/redefined_name_test.py` | 14 | ✅ All pass (100%) |
| `tests/two_stage_parse_test.py` | 7 | ✅ All pass |
| `tests/main_test.py` | 7 | ✅ All pass |
| `tests/partial_test.py` | 6 | ✅ All pass |
| `tests/conformance_test.py` | 123 | ✅ All pass (100%) |
| **Total** | **1274** | **1151 fast + 123 conformance pass (24 skipped: optional deps)** |

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
| `definition.py` (`RootNamespace`) | ~~`load_package_body()` raises `NotImplementedError` for `AliasMember` and `Import` nodes~~ **Resolved in v0.58.0** — node types were already dispatched; the real gap (imports/aliases moved to the end of the package body on public-API dump) is fixed. |
| `antlr_visitor.py` ~line 9558 | Top-level attribute multiplicity not captured (nested attributes work) |
| `definition.py` | Dead code — duplicate `elif inner_class == "ActionUsage"` block |
| `usage.py` | ~~Type relationships (`: TypeName`) not preserved in `load_from_grammar()`~~ **Fixed in v0.57.0** — `_extract_specialization_info()` hoisted to base `Usage`; new `Usage.typed_by_name` populates on all usage kinds. `typedby` object resolution is a follow-up. |
| `semantic.py` | `*`/`/` dimension derivation (`mass * speed → ForceValue` inference) not yet implemented (future); `+`/`-` dimension equality and operand-category checks are complete (v0.55.0). |
| `antlr_parser.py` | SLL error *wording* may differ from LL wording (`missing '}' at '<EOF>'` vs `extraneous input '<EOF>' ...`); source position always matches (v0.56.0). |

---

## Remaining Work

### High Priority

| Feature | Description |
|---|---|
| ~Typed-by preservation~ | **Done in v0.57.0** — `_typed_by_name` / `typed_by_name` preserved for all usage kinds loaded from grammar (`Part`, `Attribute`, `Item`, `Port`, `Action`, `Interface`, `UseCase`, `Requirement`, `State`, behavior children). Resolving `typedby` to the definition *object* via a model pass remains a follow-up. |
| ~Fix top-level attribute multiplicity~ | **Verified fixed (v0.40.0) + flags bug fixed in v0.59.0** — bounds (`[N]`, `[N..M]`, `[*]`) already survived since v0.40.0 (docs were stale); the real remaining bug was `ordered`/`nonunique` hardcoded `False` in the visitor extractors plus a `MultiplicityPart.dump()` XOR-guard that dropped `ordered`. All fixed. |
| ~AliasMember / Import handling~ | **Done in v0.58.0** — nodes were already parsed and held on `Package.imports` (definition.py); the gap was `_ensure_body()` reordering imports/aliases to the end of the body on dump. Source-order interleaving now preserved in both Model and Package rebuild paths. |

### Medium Priority

| Feature | Description |
|---|---|
| ~Feature chain type resolution~ | **Done in v0.60.0** — `ReferenceCollector` tags reference kind (`typing`/`subsetting`/`redefinition`/`subclassification`); chain check applies only to genuine feature chains (fixes false `INCOMPATIBLE_FEATURE_CHAIN` on every qualified type name like `ScalarValues::Real`). Dotted expression chains (`wheels.hub.mass`) resolve through the declared *type* of each feature, following `:>` inheritance; members of an enclosing usage's declared type (`part myCar : Car { attribute x :> engine::power; }`) resolve for `::`, `.`, and single-member references (`_resolve_through_context`); inherited chain features advance to their declared type in the compatibility check. 17 tests. |
| Connection multiplicity ends | `connect X[0..1] to Y[1]` multiplicity in connector ends |
| Nested `:>>` redefines in return | `return attribute X : Type { :>> feature = expr; }` |
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
|---|---|
| Public API classes (complete) | 28 |
| Grammar classes with `get_definition()` | **358 of 358 (100%, reflection-audited)** |
| Grammar classes with graceful fallback | All 358 (no more NotImplementedError crashes) |
| Unit + grammar + integration tests | 809 passing |
| Grammar round-trip tests passing | **143 / 143 (100%)** |
| Helper-property tests | 8 / 8 |
| Grammar-side References dispatch | ✅ | | |
| PlantUML rendering tests | **108 passing** |
| Conformance tests (2026-03 XPect suite) | **123 / 123 (100%)** |
| Semantic analysis tests | **153 passing** |
| Storage backend tests | **97 passing** (optional deps skipped if missing) |
| Bundled standard library files | 88 (kernel `.kerml` + systems `.sysml` + domain `.sysml`) |
| Library symbols indexed | ~1,604 (incl. library `function` declarations, v0.54.0) |
| PlantUML view functions | 10 (GV, PV, AFV, IV, STV, SV, CV, Tabular, DataValue, RelMatrix) |
