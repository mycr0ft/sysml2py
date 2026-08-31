# sysmlpy — TODO & Action Items

See the comprehensive [Master Development Plan](docs/DEVELOPMENT_PLAN.md) for architectural roadmap, active development phases, and planned milestones.

See [STATUS.md](STATUS.md) and [CHANGELOG.md](CHANGELOG.md) for the current project status and release history.

---

## Active Tasks (Phase D: v0.56.0+)

- [ ] **High-Performance Parsing & Graph Store Integration:**
  - [ ] ANTLR SLL fast-path prediction for large models (SLL → LL fallback)
  - [ ] `*`/`/` dimension derivation (e.g. `mass * speed` vs `ForceValue` inference)
  - [ ] Kùzu Cypher structural graph query extensions
  - [ ] NetworkX path queries / centrality analysis extensions

---

## Recently Completed

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
