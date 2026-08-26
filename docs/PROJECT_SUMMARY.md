# sysmlpy — Project Work Summary

> **For:** Future agents and team members
> **Last Updated:** August 28, 2026
> **Current Version:** v0.40.0
> **Repository:** https://github.com/mycr0ft/sysmlpy

---

## Project Overview

**sysmlpy** is a pure Python library for parsing, manipulating, and validating SysML v2.0 models. It uses an ANTLR4 parser (based on the [OMG SysML v2 grammar](https://github.com/daltskin/sysml-v2-grammar)) and provides both a programmatic API for building models and a semantic analysis engine for validating them.

### Architecture

```
sysmlpy/
├── src/sysmlpy/
│   ├── __init__.py          # Public API: loads(), load(), analyze(), load_files(), load_project()
│   ├── antlr_parser.py      # ANTLR4 lexer/parser setup
│   ├── antlr_visitor.py     # ~12.3K lines: parse tree → internal dict
│   ├── grammar/
│   │   ├── classes.py       # ~9.7K lines: grammar class hierarchy (no NotImplementedError)
│   │   └── antlr4/          # Generated ANTLR parser/lexer
│   ├── definition.py        # Model, Package, RootNamespace classes
│   ├── usage.py             # Part, Item, Attribute, Port, Action, etc.
│   ├── semantic.py          # Semantic analysis engine (~2.3K lines)
│   ├── project.py           # Multi-file project loading (load_files, load_project)
│   ├── store.py             # Storage backends (memory, NetworkX, Kuzu, Cayley)
│   ├── plantuml.py          # PlantUML diagram generation
│   ├── boxes_view.py        # Optional boxes-backed state-machine visualizer (v0.36.0)
│   ├── formatting.py        # classtree() for round-trip serialization
│   ├── navigate.py          # Searchable mixin for model traversal
│   └── library/             # Bundled SysML v2 standard library (88 files)
│       ├── kernel/          # KerML core (ScalarValues, Base, Collections, etc.)
│       ├── systems/         # SysML base (SysML.sysml)
│       └── domain/          # ISQ, SI units, base quantities
├── tests/
│   ├── grammar_test.py      # 96 round-trip tests (96 pass, 0 deferred)
│   ├── class_test.py        # 61 programmatic API tests
│   ├── main_test.py         # 7 integration tests
│   ├── plantuml_test.py     # 122 PlantUML view rendering tests
│   ├── boxes_view_test.py   # 19 boxes-backed state-machine visualizer tests (v0.36.0)
│   ├── semantic_test.py     # 124 semantic analysis tests
│   ├── project_test.py      # 17 multi-file loading tests
│   ├── navigate_test.py     # 42 model navigation tests
│   ├── import_test.py       # 21 import resolution tests
│   ├── validator_test.py    # 34 validator tests
│   ├── store_test.py        # 82 storage backend tests
│   ├── conformance_test.py  # 123 OMG XPect conformance tests
│   └── sysmlv2/             # Conformance test fixtures
└── docs/                    # Documentation
```

### Data Flow

```
SysML text → ANTLR4 Lexer/Parser → Parse Tree
    → antlr_visitor.py (parse_to_dict) → Internal dict
    → grammar/classes.py (grammar objects) → Model tree
    → usage.py / definition.py (public classes) → User-facing API
```

---

## What's Been Accomplished

### Parsing (100% Conformance)

- **ANTLR4 parser** with full SysML v2 grammar support
- **123/123 OMG XPect conformance tests pass** (100%)
- Visitor converts parse trees to internal dict representation (~12.3K lines)
- Supports all SysML v2 element types: packages, parts, items, ports, actions, states, requirements, interfaces, flows, connections, calculations, constraints, enumerations, cases, views, viewpoints, etc.

### Grammar Round-Trip

- **96/96 grammar round-trip tests pass** (100%)
- Every grammar class has `dump()` and `get_definition()` for serialization
- All 68+ `raise NotImplementedError` stubs replaced with graceful handling (v0.27.0)
- Missing classes added: `DefinitionBody`, `DefinitionBodyItem`, `FeatureSpecializationPart`, `SubclassificationPart`
- `classtree()` converts Model tree back to text

### Semantic Analysis (v0.17.0 → v0.20.1)

The semantic analysis engine (`semantic.py`) provides comprehensive validation:

| Category | Status | Details |
|----------|--------|---------|
| **Symbol Resolution** | ✅ Complete | Hierarchical symbol table with parent chain lookup |
| **Import Resolution** | ✅ Complete | Namespace (`::*`), membership, recursive (`::*::**`) |
| **Import Visibility** | ✅ Complete | `private`/`public`/`protected` enforcement |
| **Library Symbol Index** | ✅ Complete | Scans 88 `.kerml`/`.sysml` files (~1,417 symbols) |
| **Inheritance Resolution** | ✅ Complete | Supertype chain traversal for subsetting/redefinition |
| **OCL Constraints** | ✅ 8 of 8 | See table below |

### Multi-File Projects (v0.21.0)

Three new API functions enable cross-file import resolution:

| Function | Description |
|----------|-------------|
| `load_files(files, library=None)` | Load multiple files; merge packages with same name |
| `load_project(root, entry=None)` | Load all `.sysml`/`.kerml` files in a directory |
| `load_with_dependencies(entry, search_paths)` | Load entry file and recursively resolve imports |

- Package merging: files defining the same package namespace are combined
- Import resolution: cross-file type references resolve correctly
- Standard library validation: `ScalarValues`, `ISQ`, etc. recognized as valid
- 12 new tests in `tests/project_test.py`

### PlantUML View Renderings (v0.25.2 → v0.27.0)

Eight view rendering functions across two releases:

| Function | SysML v2 View | Output | Release |
|----------|--------------|--------|---------|
| `as_graphical_rendering()` | `GraphicalRendering` | PlantUML | v0.25.2 |
| `as_interconnection_diagram()` / `as_interconnection_view()` | `InterconnectionView` (`iv`) | PlantUML | v0.25.2 / v0.26.0 |
| `as_action_flow_view()` | `ActionFlowView` (`afv`) | PlantUML | v0.26.0 |
| `as_state_transition_view()` | `StateTransitionView` (`stv`) | PlantUML | v0.26.0 |
| `as_tree_diagram()` | Tree/structure | PlantUML | v0.25.2 |
| `as_element_table()` | `TabularRendering` | PlantUML | v0.25.2 |
| `as_textual_notation()` | `TextualRendering` | PlantUML | v0.25.2 |
| `as_general_view()` | `GeneralView` (`gv`) | PlantUML | v0.27.0 |
| `as_package_view()` | Package View | PlantUML | v0.27.0 |
| `as_tabular_view()` | `TabularView` (GridView) | PlantUML / MD / HTML | v0.27.0 |
| `as_data_value_tabular_view()` | Data Value Tabular View | PlantUML / MD / HTML | v0.27.0 |
| `as_relationship_matrix_view()` | Relationship Matrix View | PlantUML / MD / HTML | v0.27.0 |

**v0.27.0 additions:**
- **General View** — all SysML v2 element types; full filtering by focus/elements/depth
- **Package View** — package hierarchy with contained elements and import arrows
- **Tabular View** — GridView specialization with configurable columns; PlantUML/Markdown/HTML output
- **Data Value Tabular View** — attribute values + units; PlantUML/Markdown/HTML output
- **Relationship Matrix View** — cross-element relationship matrix; PlantUML/Markdown/HTML output
- 108 PlantUML tests total (up from 101 in v0.26.0)

**v0.26.0 features:**
- **Action Flow View** — actions + flow connections; auto-discovers flow arrows from grammar bodies
- **Interconnection View** — parts, ports, connections; `auto_include_connections` discovers bindings
- **State Transition View** — states + transitions; `auto_include_transitions` expands selection
- All views support: `focus`, `elements`, `show_external`, `auto_include_*`, `custom_style`, `direction`, B&W/color toggle, and legend

### Stylistic Checks (v0.25.5)

The `analyze()` function now includes stylistic checks that warn about naming convention violations and file-package mismatches:

| Check | Code | Severity | Description |
|-------|------|----------|-------------|
| Naming conventions | `NAMING_CONVENTION` | warning | Definitions should be PascalCase, usages camelCase, packages PascalCase, attributes/ports camelCase |
| File-package match | `FILE_PACKAGE_MISMATCH` | warning | Top-level package name should match filename (minus extension) |

- New `analyze()` parameters: `filename` (for file-package matching), `style_checks` (enable/disable, default `True`)
- All stylistic issues have severity `"warning"` rather than `"error"`
- 17 new tests in `tests/semantic_test.py`

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
| `INCOMPATIBLE_FEATURE_CHAIN` | Feature.chaining_compatible | Chained features (`a.b.c`) with incompatible types |
| `INVALID_MULTIPLICITY_BOUNDS` | Multiplicity.bounds_valid | Lower bound > upper bound (e.g., `[5..2]`) |
| `UNRESOLVED_IMPORT` | — | Import target does not exist |

### Storage Backends

- **InMemoryStore** — dict-based, zero dependencies
- **NetworkXStore** — graph analysis (shortest paths, centrality, cycles)
- **KuzuStore** — embedded graph DB with disk persistence and Cypher queries
- **CayleyStore** — remote graph DB via HTTP API

### Test Coverage

| Suite | Count | Status |
|-------|-------|--------|
| Grammar round-trip | 77 | 61 pass, 16 deferred (control-flow nodes) |
| Programmatic API | 54 | ✅ 54 pass |
| Integration (main) | 7 | ✅ 7 pass |
| PlantUML rendering | 108 | ✅ 108 pass |
| Semantic analysis | 107 | ✅ 107 pass |
| Multi-file loading | 17 | ✅ 17 pass |
| Model navigation | 33 | ✅ 33 pass |
| Import resolution | 16 | ✅ 16 pass |
| Validator | 34 | ✅ 34 pass |
| Storage backends | 46 | ✅ pass (optional deps skipped if missing) |
| Conformance | 123 | ✅ 123 pass |
| **Total** | **622** | **606 pass, 16 deferred** |

---

## Key Design Decisions

### 1. ANTLR4 over textX

The project originally used textX but migrated to ANTLR4 for better conformance with the OMG SysML v2 grammar. The textX runtime and all related files have been removed.

### 2. Grammar Class Hierarchy

The `grammar/classes.py` file contains ~354 classes that mirror the SysML v2 metamodel. Each class has:
- `__init__()` — constructs from a dict (produced by the visitor)
- `dump()` — serializes back to SysML v2 text
- `get_definition()` — serializes back to dict (for round-trip)
- `children` property — returns child elements for tree traversal

### 3. Two-Level Model

- **Grammar objects** (`grammar/classes.py`) — low-level representation of the parse tree
- **Public classes** (`usage.py`, `definition.py`) — user-friendly API with methods like `set_value()`, `_set_child()`, `find()`

The `load_from_grammar()` method on each public class bridges the two levels.

### 4. Semantic Analysis is Opt-In

The semantic analyzer (`analyze(model)`) is non-invasive and opt-in. It does not modify the model or affect parsing/loading. This was a deliberate design choice to maintain backward compatibility.

### 5. Import Visibility is Required

Per the SysML v2 spec (section 7.5.3), imports must have an explicit visibility keyword (`private`, `public`, or `protected`). The grammar enforces this — omitting the keyword produces a syntax error. The previous version allowed omission and defaulted to `private`.

### 6. Multiplicity is Stored in FeatureSpecializationPart

Multiplicity ranges (`[N]`, `[N..M]`, `[*]`) are stored as part of the `FeatureSpecializationPart` alongside typings, subsettings, and redefinitions. This is a quirk of the SysML v2 grammar where multiplicity is parsed as part of the feature specialization.

---

## Known Issues and Technical Debt

### Resolved

| Issue | Resolution |
|-------|------------|
| **Import visibility optional in grammar** | Made `visibilityIndicator` required in `SysMLv2Parser.g4` (v0.21.0) |
| **No multi-file loading support** | Added `load_files()`, `load_project()`, `load_with_dependencies()` (v0.21.0) |
| **Standard library imports not validated** | Semantic analyzer now checks `LibrarySymbolIndex` for import targets (v0.21.0) |

### High Priority

| Issue | Location | Impact |
|-------|----------|--------|
| **Action control-flow node classes missing** | `grammar/classes.py` | `IfNode`, `WhileLoopNode`, `ForLoopNode`, `ControlNode`, `SendNode`, `AcceptNode`, `TerminateNode`, etc. exist in the visitor but not in `grammar/classes.py`. 16 grammar tests fail with `KeyError`. |
| **Top-level attribute multiplicity not captured** | `antlr_visitor.py` ~line 9558 | Attributes defined at package level (not inside a definition) have `specialization=None` hardcoded, so multiplicity like `attribute x[5..2]` is lost. Nested attributes inside definitions work correctly. |
| **Typed-by not preserved in load_from_grammar** | `usage.py` (marked `#!TODO Typed By`) | When loading a model from grammar, type relationships (`: TypeName`) are not preserved on the public class objects. |
| **Duplicate ActionUsage block** | `definition.py` | Dead code — duplicate `elif inner_class == "ActionUsage"` block. |
| **PackageBodyElement name hardcoded** | `grammar/classes.py` | Comment says `#!TODO This isn't always the case`. |
| **RootNamespace doesn't handle AliasMember/Import** | `definition.py` | `load_package_body()` raises `NotImplementedError` for these node types. |

### Medium Priority

| Issue | Location | Impact |
|-------|----------|--------|
| **Feature chain type resolution incomplete** | `semantic.py` `_get_feature_type()` | Can resolve the type of the first feature in a chain but not subsequent features (requires full type resolution). |
| **Connector end compatibility is a stub** | `semantic.py` `_check_connector_ends_compatible()` | Returns empty list — full implementation requires resolving types of both connector ends and checking assignability. |
| **Library symbol extraction is regex-based** | `semantic.py` `LibrarySymbolIndex` | Uses regex patterns to extract symbols from `.kerml`/`.sysml` files rather than parsing them. May miss edge cases or produce false positives. |
| **`_find_definition_by_name` walks entire model** | `semantic.py` | O(n) search through the entire model tree. Could be optimized with an index. |

### Low Priority

| Issue | Location | Impact |
|-------|----------|--------|
| **No OCL constraint on succession source/target** | `semantic.py` | SuccessionAsUsage source and target should be actions — not validated. |
| **No OCL constraint on requirement subject** | `semantic.py` | Requirements should have a subject parameter — not validated. |
| **No OCL constraint on flow payload compatibility** | `semantic.py` | Flow payload must be compatible with source/target — not validated. |

---

## Future Work

### Semantic Analysis Extensions

1. **Full type resolution for feature chains** — Currently only resolves the first feature's type. Full implementation would resolve types through the entire chain (`a.b.c` where `a: A`, `A` has `b: B`, `B` has `c: C`).

2. **Connector end type compatibility** — Validate that connected ends have compatible types (e.g., a `Port` end can only connect to another `Port` end).

3. **Succession source/target validation** — Ensure succession source and target are actions.

4. **Requirement subject validation** — Ensure requirements have a subject parameter.

5. **Flow payload compatibility** — Ensure flow payload is compatible with source and target ends.

6. **Multiplicity bounds on expressions** — Currently only validates literal integer bounds. Variable references (e.g., `[i..j]`) and expressions are not validated.

7. **Cardinality constraint propagation** — When a feature is subsetted, the subsetting feature's multiplicity must be a subset of the subsetted feature's multiplicity.

### Parser and Grammar

8. **Fix top-level attribute multiplicity** — The visitor hardcodes `specialization=None` for top-level attributes. This requires updating the visitor to call `_build_full_specialization_from_ctx` for attribute usages.

9. **Typed-by preservation** — Preserve type relationships when loading from grammar in `load_from_grammar()`.

10. **AliasMember and Import handling** — Implement `load_package_body()` support for these node types.

### Library and Standard Compliance

11. **Parse library files instead of regex extraction** — Replace `LibrarySymbolIndex._extract_from_file()` with actual parsing of `.kerml`/`.sysml` files for accurate symbol discovery.

12. **Standard library loading** — ~~Currently library symbols are indexed but not loaded as actual model objects.~~ Partially resolved in v0.21.0: `load_files()` and `load_with_dependencies()` accept a `library` parameter that validates standard library imports. Full resolution would parse library files and make them available for symbol resolution in `analyze()`.

13. **OCL constraint library** — Consider maintaining a machine-readable OCL constraint library that can be extended without code changes.

### Performance

14. **Symbol table indexing** — Add an index for `_find_definition_by_name` to avoid O(n) model traversal.

15. **Lazy semantic analysis** — Currently all constraints are checked on every `analyze()` call. Consider lazy evaluation or incremental analysis.

16. **Caching for library symbol index** — Already implemented, but consider disk caching for faster startup.

### Documentation

17. **API documentation** — Generate API docs from docstrings (Sphinx or MkDocs).

18. **Semantic analysis guide** — Dedicated documentation page for using `analyze()` and interpreting results.

19. **Multi-file project guide** — Document `load_files()`, `load_project()`, and `load_with_dependencies()` with examples for common project structures.

---

## Potential Pitfalls

### 1. Grammar Class `children` Property is Fragile

The `children` property on grammar classes uses `getattr(self, "children", [])` which returns an empty list for classes that don't have a `children` attribute. This is convenient but can mask bugs where a class should have children but doesn't.

**Mitigation:** Always verify the class has a `children` attribute before relying on it. Use `hasattr()` if uncertain.

### 2. Visitor Dict Structure is Not Typed

The internal dict produced by `antlr_visitor.py` is not typed or validated. Changes to the visitor can silently break grammar classes that expect specific keys.

**Mitigation:** Run the full test suite after any visitor changes. Consider adding a schema validator for the dict structure.

### 3. Multiplicity Structure is Deeply Nested

The multiplicity structure is 5 levels deep: `FeatureSpecializationPart → MultiplicityPart → OwnedMultiplicity → MultiplicityRange → MultiplicityExpressionMember → MultiplicityRelatedElement → LiteralInteger`. This makes it easy to get the navigation wrong.

**Mitigation:** Use the `_extract_bound_value_from_member()` helper in `semantic.py` as a reference for correct navigation.

### 4. Import Visibility Propagation is Complex

The `_propagate_public_imports()` method handles three visibility levels with different propagation rules. Adding new visibility levels or changing rules requires careful testing.

**Mitigation:** The `TestImportVisibility` test class covers the key scenarios. Add new tests when modifying visibility logic.

### 5. Symbol Table and Model Tree are Separate

The `SymbolTable` is built from the model tree but is a separate data structure. Changes to the model after `analyze()` is called will not be reflected in the symbol table.

**Mitigation:** Document that `analyze()` should be called after all model modifications are complete.

### 8. Multi-File Package Merging

When `load_files()` merges packages with the same name, children are appended without deduplication. If two files define the same element name within the same package, both will exist in the merged model and may trigger `DUPLICATE_NAME` warnings during analysis.

**Mitigation:** Use `analyze()` after loading to detect duplicate names. Ensure project files define non-overlapping elements within shared packages.

### 6. ANTLR Grammar Updates Require Visitor Updates

When the OMG releases a new SysML v2 grammar, the ANTLR parser must be regenerated and the visitor updated to handle any new rules.

**Mitigation:** The conformance test suite (123 tests) serves as a regression test. Run it after any grammar update.

### 7. Python 3.13 Compatibility

The project runs on Python 3.13.5. Some dependencies (like `antlr4-python3-runtime`) may have compatibility issues with newer Python versions.

**Mitigation:** Pin dependency versions in `pyproject.toml`. Test on multiple Python versions if expanding support.

---

## Quick Reference

### Running Tests

```bash
# All tests
pytest tests/

# Specific suites
pytest tests/grammar_test.py        # Round-trip
pytest tests/class_test.py          # Programmatic API
pytest tests/semantic_test.py       # Semantic analysis
pytest tests/project_test.py        # Multi-file loading
pytest tests/store_test.py          # Storage backends
pytest tests/conformance_test.py    # OMG conformance (slow)

# Skip conformance (fast development)
pytest -m "not conformance"
```

### Adding a New OCL Constraint

1. Add a check method to `SemanticAnalyzer` in `semantic.py`:
   ```python
   def _check_my_constraint(self, model: Any, symtab: SymbolTable) -> list[SemanticIssue]:
       issues: list[SemanticIssue] = []
       # Walk model, check constraint, append issues
       return issues
   ```

2. Call it from `analyze()`:
   ```python
   issues.extend(self._check_my_constraint(model, symtab))
   ```

3. Add tests to `tests/semantic_test.py`:
   ```python
   class TestMyConstraint:
       def test_violation(self):
           model = loads("...")
           issues = analyze(model)
           assert any(i.code == "MY_CONSTRAINT" for i in issues)
   ```

### Adding a New Storage Backend

1. Subclass `Store` in `store.py`:
    ```python
    class MyStore(Store):
        def put(self, element_id: str, data: dict) -> None: ...
        def get(self, element_id: str) -> Optional[dict]: ...
        # ... implement all abstract methods
    ```

2. Register in `create_store()`:
    ```python
    elif backend == "my":
        return MyStore(**kwargs)
    ```

3. Add tests to `tests/store_test.py` using the parameterized test patterns.

### Adding Multi-File Loading Support

The `project.py` module handles multi-file loading:

1. `load_files()` parses each file and merges packages with the same name
2. `load_project()` discovers all `.sysml`/`.kerml` files in a directory
3. `load_with_dependencies()` extracts imports via regex and recursively loads dependencies

To extend import resolution, modify `_extract_imports()` and `_find_import_file()` in `project.py`.

---

## Contact

- **Author:** Jon R. Fox (mycr0ft) — jon.fox@drfox.com
- **Repository:** https://github.com/mycr0ft/sysmlpy
- **Issues:** https://github.com/mycr0ft/sysmlpy/issues
