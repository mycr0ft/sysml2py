# AGENTS.md — AI Agent Onboarding Guide for sysmlpy

This file gives AI coding agents (Claude, GPT, Gemini, etc.) the context needed
to work effectively on the sysmlpy codebase without re-discovering what the team
already knows.

---

## Project Identity

| Field | Value |
|-------|-------|
| Name | sysmlpy |
| Current version | 0.36.0 |
| Language | Python 3.9+ |
| Package manager | **Poetry** (use `poetry run` for all commands) |
| Test runner | pytest via `poetry run pytest` |
| Primary entry point | `src/sysmlpy/__init__.py` |
| Repository | https://github.com/mycr0ft/sysmlpy |

---

## Running Tests

Always use Poetry. There is no system-level `python` or `pip` available.

```bash
# All non-conformance tests (fast, ~2–3 min)
poetry run pytest tests/ -m "not conformance" --tb=short -q

# Grammar round-trip only
poetry run pytest tests/grammar_test.py --tb=short -q

# Conformance suite (slow, ~5–10 min)
poetry run pytest -m conformance --tb=short -q

# Single test file
poetry run pytest tests/class_test.py --tb=short -q

# All tests
poetry run pytest tests/ --tb=short -q
```

### Grammar test status

All **79 grammar round-trip tests pass** (100%) as of v0.31.3+.

---

## Architecture in One Page

```
SysML text
  → ANTLR4 Lexer/Parser       antlr_parser.py
  → Parse Tree
  → antlr_visitor.py           parse_to_dict() → internal dict (~12.3K lines)
  → grammar/classes.py         grammar object hierarchy (~9.7K lines, ~354 classes)
  → usage.py / definition.py   public API: Part, Item, Attribute, Port, …
  → plantuml.py                view rendering (8 view functions + helpers)
  → semantic.py                SemanticAnalyzer, SymbolTable
  → store.py                   InMemoryStore, NetworkXStore, KuzuStore, CayleyStore
```

### Key files

| File | Purpose |
|------|---------|
| `src/sysmlpy/__init__.py` | Public API: `loads()`, `load()`, `analyze()`, `load_files()`, etc. |
| `src/sysmlpy/antlr_visitor.py` | ~12.3K lines — ANTLR parse tree → internal dict |
| `src/sysmlpy/grammar/classes.py` | ~9.7K lines — grammar class hierarchy |
| `src/sysmlpy/definition.py` | `Model`, `Package`, `RootNamespace` |
| `src/sysmlpy/usage.py` | `Part`, `Item`, `Attribute`, `Port`, `Action`, `State`, etc. |
| `src/sysmlpy/plantuml.py` | All `as_*_view()` functions and `PlantUMLGenerator` |
| `src/sysmlpy/semantic.py` | `analyze()`, `SemanticAnalyzer`, `SymbolTable`, `LibrarySymbolIndex` |
| `src/sysmlpy/project.py` | `load_files()`, `load_project()`, `load_with_dependencies()` |
| `src/sysmlpy/store.py` | Storage backends |
| `src/sysmlpy/boxes_view.py` | Optional boxes-backed state-machine visualizer |
| `src/sysmlpy/formatting.py` | `classtree()` — model tree → SysML text |
| `pyproject.toml` | Version is in `[project].version` (PEP 621) |

---

## Conventions

### Version bumping

Version string appears in **two** places — update both together:

1. `src/sysmlpy/__init__.py` — `__version__ = "X.Y.Z"`
2. `pyproject.toml` — `[project] version = "X.Y.Z"`

### Grammar class pattern

Every class in `grammar/classes.py` follows this interface:

```python
class MyClass:
    def __init__(self, d: dict):
        # parse fields from d
        self.children = []

    def dump(self) -> str:
        # return SysML text representation
        return ""

    def get_definition(self) -> dict:
        # return round-trip dict (mirrors visitor output)
        return {}
```

**Never add `raise NotImplementedError`** — replace with graceful fallback
(print a warning and skip/no-op). This is the v0.27.0 contract.

### Catch-all pattern for unknown visitor dict keys

```python
else:
    print(f"[ClassName] Unknown element type: {elem.get('name', elem)}")
```

### Adding a new grammar class

1. Find where the visitor emits the dict key (search `antlr_visitor.py` for the string)
2. Find the dispatch table in the parent class `__init__` that should instantiate it
3. Add the class with `__init__`, `dump()`, `get_definition()`, `children`
4. Add a test in `tests/grammar_test.py`

---

## Test File Map

| File | Count | What it tests |
|------|-------|--------------|
| `grammar_test.py` | 79 (all pass) | Parse → grammar object → `dump()` round-trips |
| `class_test.py` | 54 | Programmatic API: `Part()`, `Action()`, `dump()`, etc. |
| `main_test.py` | 7 | `load()` / `loads()` / `load_grammar()` public API |
| `plantuml_test.py` | 108 | All `as_*_view()` functions |
| `semantic_test.py` | 107 | `analyze()`, OCL checks, symbol resolution, imports |
| `navigate_test.py` | 33 | `Searchable` mixin, model traversal |
| `import_test.py` | 31 | Import visibility/round-trip, `add_import()`, `.imports`, source-order preservation |
| `validator_test.py` | 34 | Validator rules |
| `project_test.py` | 17 | `load_files()`, `load_project()` |
| `store_test.py` | 46 | Storage backends (networkx/kuzu are skipped if not installed) |
| `conformance_test.py` | 123 | OMG 2026-03 XPect parse conformance (slow) |

---

## Common Pitfalls

### 1. `children` property is load-bearing

Many traversal functions call `obj.children`. Every grammar class must set
`self.children = [...]` in `__init__`. Missing it causes `AttributeError` in
downstream code, not in the class itself.

### 2. Visitor dict structure is untyped

The dict from `antlr_visitor.py` uses string keys like `"name"`,
`"ownedRelationship"`, `"ownedRelatedElement"`, `"memberElement"`. These are
not documented in one place — grep `antlr_visitor.py` to find what a rule emits.

### 3. Multiplicity is 5 levels deep

```
FeatureSpecializationPart
  → MultiplicityPart
    → OwnedMultiplicity
      → MultiplicityRange
        → MultiplicityExpressionMember
          → MultiplicityRelatedElement
            → LiteralInteger
```

Use `_extract_bound_value_from_member()` in `semantic.py` as the canonical
navigation helper.

### 4. `pyproject.toml` has version in one place

`pyproject.toml` uses PEP 621 `[project] version = "X.Y.Z"`. Also bump
`src/sysmlpy/__init__.py:__version__` to match. (Older releases had a
`[tool.poetry].version` field too — it is no longer present in this
project's `pyproject.toml`.)

### 5. Top-level attribute multiplicity is lost

`antlr_visitor.py` hardcodes `specialization=None` for top-level attribute
usages (~line 9558). Nested attributes inside definitions work correctly.
Do not report this as a bug you discovered — it is a known issue.

### 6. Type relationships: name preserved, object resolution is not

Since v0.57.0, `load_from_grammar()` preserves the declared type *name* on
all usage kinds — use `obj.typed_by_name` (e.g. `"Engine"`,
`"ScalarValues::Real"`). What is still **not** preserved is the resolved
definition *object* in `obj.typedby`; that is only set when wired
programmatically via `set_typed_by()`. A model-wide resolution pass is a
tracked follow-up (see TODO.md).

---

## PlantUML View Functions

All live in `src/sysmlpy/plantuml.py` and are exported from `__init__.py`.

| Function | SysML v2 short name | Output formats |
|----------|--------------------|----|
| `as_general_view()` | `gv` | PlantUML |
| `as_package_view()` | — | PlantUML |
| `as_action_flow_view()` | `afv` | PlantUML |
| `as_interconnection_view()` | `iv` | PlantUML |
| `as_state_transition_view()` | `stv` | PlantUML |
| `as_tabular_view()` | GridView | PlantUML / Markdown / HTML |
| `as_data_value_tabular_view()` | GridView | PlantUML / Markdown / HTML |
| `as_relationship_matrix_view()` | GridView | PlantUML / Markdown / HTML |

All accept: `focus`, `elements`, `style` (`"bw"` or `"color"`), `direction`,
`custom_style`, and view-specific flags like `auto_include_connections`.

---

## Before You Finish a Task

1. Run `poetry run pytest tests/class_test.py tests/main_test.py tests/repr_test.py tests/navigate_test.py tests/grammar_test.py tests/semantic_test.py --tb=short -q` and confirm all pass.
2. If you touched `grammar/classes.py`, also run
   `poetry run pytest tests/grammar_test.py --tb=short`.
3. If you touched `plantuml.py`, run
   `poetry run pytest tests/plantuml_test.py --tb=short`.
4. If you touched `semantic.py`, run
   `poetry run pytest tests/semantic_test.py --tb=short`.
5. If you bumped the version, update all three locations listed above.
6. Update `CHANGELOG.md`, `STATUS.md`, and `docs/PROJECT_SUMMARY.md`.

---

## CAD / Shape Modeling Extracted

The parametric CAD bridge (`sysmlpy.cad.*`, `tests/cad_test.py`) was extracted
into a **separate project** at `/storage16/home/jfox/sysmlcad/`.

- Package name: **`sysmlcad`** (import `from sysmlcad import ...`)
- Depends on `sysmlpy` as a sibling via path dependency
- Uses Poetry: `cd ../sysmlcad && poetry run pytest`
- Contains the Shape IR, expression system, pluggable backend registry, and
  OpenSCAD backend (85 tests)
- Upstream: no files from the CAD module remain in the sysmlpy tree

---

## Future Project: sysmlpad — SysML v2 Diagram Editor

A standalone interactive diagram editor using **Gaphas** (GTK4 + Cairo) +
**sysmlpy** as the model backend.

- **Gaphas** provides the canvas, constraint solver, items (Element/Line),
  handles, zoom/pan, GTK integration — all manual positioning for free.
- **sysmlpy** provides parsing, grammar classes (354 types), semantic
  analysis, round-trip `dump()`, and PlantUML export.
- A thin adapter layer maps sysmlpy grammar classes to Gaphas Items.

  ```
  .sysml file → sysmlpy.parse() → adapter → Gaphas Canvas → GTK Window
                   ↑                              ↓ user drags/resizes
                   ← sysmlpy.dump()  ← adapter  ←
  ```

- Estimate: ~4–6 weeks for structural subset (parts, ports, connections, BDD).
