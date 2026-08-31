# sysmlpy — TODO & Action Items

See the comprehensive [Master Development Plan](docs/DEVELOPMENT_PLAN.md) for architectural roadmap, active development phases, and planned milestones.

See [STATUS.md](STATUS.md) and [CHANGELOG.md](CHANGELOG.md) for the current project status and release history.

---

## Active Tasks (Phase C: v0.55.0)

- [ ] **Expression Type Checking & Static Evaluation:**
  - [ ] Operator operand type compatibility (numeric, boolean, string) on the structured expression AST
  - [ ] Pint unit-dimension compatibility checking inside expressions (`[m] + [kg]` → error)
  - [ ] Constant folding / static expression reduction (e.g. `10 [kg] * 2` → `20 [kg]`)

---

## Recently Completed

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

- [ ] **Phase D (v0.56.0+):** ANTLR SLL mode fast-path parsing & graph store query enhancements
