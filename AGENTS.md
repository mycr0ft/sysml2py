# AGENTS.md — AI Agent Onboarding Guide for sysmlpy

This file gives AI coding agents (Claude, GPT, Gemini, etc.) the context needed
to work effectively on the sysmlpy codebase without re-discovering what the team
already knows.

---

## Project Identity

| Field | Value |
|-------|-------|
| Name | sysmlpy |
| Current version | 0.87.0 |
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

All **153 grammar round-trip tests pass** (100%) as of v0.87.0.

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
| `src/sysmlpy/diff.py` | Semantic model diff (`diff_models`, `diff_files`, `ModelDiff`) |
| `src/sysmlpy/sim.py` | State-machine simulation (optional `sim` extra, `transitions` library) |
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

Counts from `pytest --collect-only` at v0.87.0 (1609 total: 1486 + 123 conformance).

| File | Count | What it tests |
|------|-------|--------------|
| `grammar_test.py` | 153 (all pass) | Parse → grammar object → `dump()` round-trips |
| `class_test.py` | 79 | Programmatic API: `Part()`, `Action()`, `dump()`, etc. |
| `main_test.py` | 7 | `load()` / `loads()` / `load_grammar()` public API |
| `partial_test.py` | 7 | Partial-parse recovery (`loads_partial` / `load_partial`) |
| `resolve_test.py` | 12 | `Model.resolve_types()` typedby resolution |
| `reference_parse_test.py` | 12 | `ref` usages in the object tree (all forms) |
| `constraint_text_test.py` | 12 | `rep`/rescued constraint textual bodies |
| `plantuml_test.py` | 151 | All `as_*_view()` functions |
| `semantic_test.py` | 179 | `analyze()`, OCL checks, symbol resolution, imports |
| `evaluator_test.py` | 44 | Conditional expressions, calc ``in`` parameter invocation, recursion, what-if bindings |
| `navigate_test.py` | 42 | `Searchable` mixin, model traversal |
| `import_test.py` | 31 | Import visibility/round-trip, `add_import()`, `.imports`, source-order preservation |
| `validator_test.py` | 84 | Validator rules (+ state-machine/trigger/requirement/trace/direction/satisfy/connector checks) |
| `diff_test.py` | 41 | Semantic model diff: rename detection, grammar fields, state-machine diff, trace edges, change-rate gate |
| `project_test.py` | 21 | `load_files()`, `load_project()` |
| `dfa_cache_test.py` | 14 | Persistent DFA cache: round-trip equivalence, fallbacks, env/`set_dfa_cache` config, cross-process save/load |
| `store_test.py` | 121 | Storage backends (networkx/kuzu skipped if not installed; Cayley tests skipped without a live server: `podman run -d --name cayley -p 64210:64210 docker.io/cayleygraph/cayley`) |
| `kuzu_store_test.py` | 32 | KùzuStore against a local database (skipped if `kuzu` is not installed) |
| `cayley_store_test.py` | 39 | CayleyStore against a live server at localhost:64210 (skipped when the server is down) |
| `conformance_test.py` | 123 | OMG 2026-03 XPect parse conformance (slow; `-m conformance`) |
| `sim_test.py` | 52 | State-machine simulation: guards, executing assignment effects, history pseudostates (`sim` extra) |
| `cli_test.py` | 39 | `sysmlpy` CLI commands (`python -m sysmlpy`) |
| `lsp_test.py` | 37 | Language Server Protocol server (position/completion/hover) |
| `lsp_batch4_test.py` | 36 | LSP batch-4 features (references, rename, semantic tokens) |
| `traceability_test.py` | 46 | Requirement traceability matrices and satisfy/verify edges |
| `interchange_test.py` | 38 | JSON-LD / property-interchange export-import round-trips |
| `spreadsheet_test.py` | 37 | Spreadsheet (Excel/CSV) export/import views |
| `repr_test.py` | 34 | `repr()` output for grammar and API objects |
| `boxes_view_test.py` | 54 | Boxes-backed state-machine visualizer (`boxes_view.py`) |
| `redefined_name_test.py` | 14 | `redefined_name` resolution edge cases |
| `two_stage_parse_test.py` | 12 | Two-stage parse pipeline (dict → grammar classes) |
| `palette_test.py` | 6 | PlantUML color palette (Okabe-Ito) |

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

### 5. Top-level attribute multiplicity — RESOLVED (v0.59.0)

Multiplicities on top-level usages (`attribute x[5..2]`, `part w[4]
ordered`) round-trip correctly — bounds since v0.40.0, `ordered`/`nonunique`
flags since v0.59.0. The old "specialization=None" note was stale. Note:
`nonunique ordered` canonicalizes to `ordered nonunique` on dump
(grammatically identical).

### 6. Type relationships: name preserved, object resolution is not

Since v0.57.0, `load_from_grammar()` preserves the declared type *name* on
all usage kinds — use `obj.typed_by_name` (e.g. `"Engine"`,
`"ScalarValues::Real"`). The resolved definition *object* in `obj.typedby`
is set by programmatic `set_typed_by()` and, since v0.79.0, by the opt-in
`model.resolve_types()` pass (idempotent, dump-stable; library typings
stay name-only). Note: setting `typedby` is serialization-safe only
through the `_typedby_serialized_elsewhere` guard in
`Usage._get_definition` — a def already in the tree must not be inserted
again as a package member.

### 7. Bare `import` without a visibility keyword is non-conformant — RESOLVED

The OMG SysML v2 standard **requires** a visibility declaration on imports
(`private import ...`, `public import ...`, `protected import ...`);
confirmed against the textual standard and the XPect source in a prior
session. The grammar's `importRule` intentionally rejects bare
`import X::*;` with `SysMLSyntaxError` (see `tests/import_test.py`).
Do **not** "fix" the parser or file a conformance-gap TODO for this.

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
6. **Tag the release and push the tag** — the PyPI publish + GitHub
   Release job only fires on `v*` **tag** pushes, never on plain
   commits to `main`:
   ```bash
   git tag -a v0.X.Y -m "v0.X.Y: description" && git push origin v0.X.Y
   ```
   (Missed tags are recoverable: tag the historical commits and push —
   the workflow builds the version recorded in each commit's tree.
   v0.58.0–v0.64.0 were back-tagged on 2026-09-03 after 0.57.0–0.64.0
   went out untagged.)
7. Update `CHANGELOG.md`, `STATUS.md`, and `docs/PROJECT_SUMMARY.md`.

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
