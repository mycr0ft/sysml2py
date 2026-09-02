# sysmlpy — TODO & Action Items

See the comprehensive [Master Development Plan](docs/DEVELOPMENT_PLAN.md) for architectural roadmap, active development phases, and planned milestones.

See [STATUS.md](STATUS.md) and [CHANGELOG.md](CHANGELOG.md) for the current project status and release history.

---

## Active Tasks (Post-Phase-D candidates)

Phases A–D from the [Master Development Plan](docs/DEVELOPMENT_PLAN.md)
are complete.  Candidate follow-up work:

- [ ] `*`/`/` unit-dimension derivation (e.g. `mass * speed` vs `ForceValue` inference)
- [ ] SLL error-message parity (align ANTLR wording between prediction modes)
- [ ] Persistent DFA cache serialization to eliminate cold-start parse cost
- [ ] Visitor performance profiling (`parse_to_dict` dominates end-to-end time)
- [ ] CayleyStore query extensions (parity with NetworkX/Kùzu)

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
