# sysmlpy — TODO & Action Items

See the comprehensive [Master Development Plan](docs/DEVELOPMENT_PLAN.md) for architectural roadmap, active development phases, and planned milestones.

See [STATUS.md](STATUS.md) and [CHANGELOG.md](CHANGELOG.md) for the current project status and release history.

---

## Active Tasks (Post-Phase-D candidates)

Phases A–D from the [Master Development Plan](docs/DEVELOPMENT_PLAN.md)
are complete.  Follow-up work is organized under the
[Adoption Roadmap](docs/DEVELOPMENT_PLAN.md#6-adoption-roadmap-v061--making-sysmlpy-useful-to-systems-engineers)
(§6 of the plan) — goals to make sysmlpy useful to systems engineers:

- [x] **Goal 1 — CLI: `analyze` + `view` commands with exit codes** *(v0.61.0: `sysmlpy analyze FILE... [--format json] [--fail-on ...]`, `sysmlpy view FILE --view NAME [--focus ...] [-o ...]`, `parse`/`format` subcommands, documented 0/1/2 exit codes, legacy flat form preserved; 39 tests in `tests/cli_test.py`)*
- [x] **Goal 2 — Requirement traceability & verification coverage** *(v0.62.0: `verification def`/`verification` usages and `verify` members (reference + inline declaration forms) parse and round-trip; `Requirement.subject`/`.verified_by` extraction; new `sysmlpy.traceability` module with `extract_traceability` → `TraceabilityReport` (coverage queries, text/markdown/json output) and `as_traceability_matrix_view` (markdown/html/plantuml); `sysmlpy trace` CLI with `--fail-on uncovered` exit gate; 46 tests in `tests/traceability_test.py`)*
- [x] **Goal 3 — JSON interchange format** *(v0.63.0: `sysmlpy.interchange` module — `to_interchange()` / `from_interchange()` JSON-LD-style partition documents (flat `@graph`, `@id`/`@type` elements, deterministic uuid5 ids); lossless import back to a live model via the shared `Model._load_definition()` path; `sysmlpy export` / `sysmlpy import` CLI commands; 38 tests in `tests/interchange_test.py`. Spec-normative JSON-LD context mapping (OMG property IRIs) tracked as follow-up.)*
- [x] **Goal 4 — Expression evaluator** *(v0.64.0: `sysmlpy.evaluator` — `collect_values()` / `evaluate_expression()` / `evaluate_calculation()` / `check_constraints()`; pint attribute values bind into calc/constraint evaluation with what-if `bindings`; feature-chain resolution with type fallback; glued unit-expression handling; `sysmlpy eval` CLI with `--expr`/`--set`/`--constraints`; calc defs inside part bodies no longer dropped by the visitor/object tree; 44 tests in `tests/evaluator_test.py`. Conditional expressions and calc `in` parameters tracked as follow-up.)*
- [x] **Goal 5 — LSP server** *(v0.65.0: `sysmlpy.lsp` package — dependency-free LSP 3.17 subset over stdio JSON-RPC; `publishDiagnostics` (exact ANTLR syntax ranges + `analyze()` issues located via quoted-name heuristic), `documentSymbol` outline, `hover` (kind/type/value), `definition` (usage→decl, type name→type def), keyword+member `completion`, FULL text sync, UTF-16 positions; `sysmlpy-lsp` console script + `python -m sysmlpy.lsp`; VS Code extension scaffold `editors/vscode/sysmlpy-lsp/`; Neovim recipes in `docs/LSP.md`; 37 tests in `tests/lsp_test.py`. Follow-ups: incremental sync, position-tracked semantic diagnostics, workspace/symbol, `.`-completion.)*
- [~] **Goal 6 — Rendering without Java** (native SVG / Mermaid output; boxes covers state machines only)
  - [x] **Phase 1 (v0.67.0)** — PlantUML notation fidelity: edge encodings aligned to the OMG pilot
    (thick plain connections, heaviest bindings, `--:|>` typing, `--||>` redefinition, send/accept
    actions, variant/objective/metadata, succession flow); connection endpoints now parse (visitor
    stub fixed); gv `auto_include_connections` edges; stv nested composite-state blocks; legends
    updated. Ground truth: OMG pilot PlantUML generator + official Graphical Notation figures;
    research corpus at `~/research/notation_corpus/` (NOTATION_RESEARCH.md). Next: boxes engine
    (rename pending — PyPI name collision) for Java-free SVG/braille; traceability matrix md/html
    already exists in `traceability.py`.
- [x] **Goal 7 — Spreadsheet bridge** *(v0.66.0: `sysmlpy.spreadsheet` — CSV export of tabular/data-value/matrix views (`output_format="csv"`, `view --format csv`), `write_xlsx()` workbook export + `sysmlpy xlsx` CLI (optional `openpyxl` extra `sysmlpy[xlsx]`), value import into evaluator bindings (`import_values_csv()`/`import_values_xlsx()`, `eval --set-file`, `parse_value_literal()`); 37 tests in `tests/spreadsheet_test.py`.)*
- [ ] **Goal 8 — Semantic model diff** (review workflows)
- [ ] **Goal 9 — Validator depth** (more OCL well-formedness checks)
- [ ] **Goal 10 — Technical stubs** (connector-end compatibility, `*`/`/` unit derivation, SLL error parity, regex→parser library extraction, Cayley parity)

Legacy candidate follow-up work:

- [ ] `*`/`/` unit-dimension derivation (e.g. `mass * speed` vs `ForceValue` inference) *(→ Goal 10)*
- [ ] SLL error-message parity (align ANTLR wording between prediction modes) *(→ Goal 10)*
- [ ] Persistent DFA cache serialization to eliminate cold-start parse cost
- [ ] Visitor performance profiling (`parse_to_dict` dominates end-to-end time)
- [ ] CayleyStore query extensions (parity with NetworkX/Kùzu) *(→ Goal 10)*

---

## Recently Completed

- [x] **v0.60.0:** Feature chain type resolution (Medium Priority from STATUS.md)
  - [x] `ReferenceCollector` tags reference kind (`typing`/`subsetting`/`redefinition`/`subclassification`)
  - [x] Chain check restricted to subsetting/redefinition — fixes false `INCOMPATIBLE_FEATURE_CHAIN` on every qualified type name (`ScalarValues::Real`)
  - [x] Dotted expression chains (`wheels.hub.mass`) resolve through declared types incl. `:>` inheritance (`_resolve_feature_chain` + `_resolve_segment_through_type`)
  - [x] Members of an enclosing usage's declared type resolve for `::`, `.`, and single-member references in usage bodies (`_resolve_through_context`; `part myCar : Car { attribute x :> engine::power; }`)
  - [x] Inherited chain features advance to their *declared type* in the compatibility check (was advancing to the declaring supertype)
  - [x] 17 regression tests in `tests/semantic_test.py` (`TestFeatureChainTypeResolution`)

- [x] **v0.59.0:** Top-level multiplicity — verified bounds fixed since v0.40.0 (stale docs); fixed real residual bug: `ordered`/`nonunique` flags hardcoded `False` in both visitor multiplicity extractors + `MultiplicityPart.dump()` XOR-guard dropping `ordered`. 7 tests.
- [x] **v0.58.0:** Import / AliasMember source-order preservation (High Priority from STATUS.md)
  - [x] Both `_ensure_body()` rebuild paths (Model + Package) re-emit `Import`/`AliasMember` at original positions
  - [x] Root-level and interleaved imports/aliases round-trip through `loads(...).dump()`
  - [x] 10 regression tests in `tests/import_test.py` (`TestImportSourceOrder`)

- [x] **v0.57.0:** Typed-by preservation (High Priority from STATUS.md)
  - [x] `_extract_specialization_info()` hoisted from `Action` to base `Usage`; handles both grammar layouts
  - [x] New `Usage.typed_by_name` property populated on `loads()` for all usage kinds (Part, Item, Attribute, Port, Connection, Action, Interface, UseCase, Requirement, State, behavior children)
  - [x] 7 regression tests in `tests/class_test.py`
  - [ ] Follow-up: resolve `typedby` to the definition *object* via a model pass

- [x] **Phase D (v0.56.0):** High-performance parsing & graph store queries
  - [x] Two-stage SLL → LL parse with single-build fast path (38% faster parse)
  - [x] `prediction_mode=` parameter (sll / ll / sll_only)
  - [x] NetworkX: `all_paths`, `descendants_depth_limited`, `neighborhood`, `impact_analysis`, in/out-degree centrality
  - [x] Kùzu: `execute_cypher` passthrough, `shortest_path_between_named`, `siblings`, `hub_elements`

- [x] **Phase C (v0.55.0):** Expression type checking & unit safety
  - [x] `OPERAND_TYPE_MISMATCH` for logical/relational/equality/arithmetic rules
  - [x] `UNIT_DIMENSION_MISMATCH` for `+`/`-` on differing ISQ dimensions (pint-backed)
  - [x] `const_fold()` static reduction incl. safe parenthesized-text arithmetic
  - [x] Structured boolean-keyword emission (`and`/`or`/`xor`/`implies`) + round-trip
  - [x] `**`/`^` exponentiation split; `true`/`false` as `LiteralBoolean` primaries

- [x] **Phase B (v0.54.0):** Name resolution on structured expressions
  - [x] `_walk_expression_identifiers` + `ExpressionIdentifierCollector` in `semantic.py`
  - [x] Resolution for constraints, assert constraints, calc bodies, attribute defaults, guards
  - [x] Dotted feature-chain segment resolution (`wheel1.hub.mass`)
  - [x] `UNRESOLVED_EXPRESSION_IDENTIFIER` errors for unresolved names
  - [x] Library index captures `function` declarations; bundled library indexed by default

- [x] **Phase A (v0.53.1):** Grammar Class Integrity & 100% Parse Conformance
  - [x] `get_definition()` added to all 36 missing classes (reflection audit: 358/358)
  - [x] `ReturnParameterMember` list-vs-dict round-trip bug fixed
  - [x] `Import_Visibility_Valid.error` updated; XPect conformance 123/123 (100%)

---

## Upcoming Milestones

- (none — Phase D is the final planned phase; see docs/DEVELOPMENT_PLAN.md)
