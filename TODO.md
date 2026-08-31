# sysmlpy — TODO & Action Items

See the comprehensive [Master Development Plan](docs/DEVELOPMENT_PLAN.md) for architectural roadmap, active development phases, and planned milestones.

See [STATUS.md](STATUS.md) and [CHANGELOG.md](CHANGELOG.md) for the current project status and release history.

---

## Active Tasks (Phase B: v0.54.0)

- [ ] **Name Resolution on Structured Expressions:**
  - [ ] Expression AST walker (`_walk_expression_identifiers`) in `semantic.py`
  - [ ] Symbol resolution for `FeatureReferenceExpression` / `FeatureChainMember` against `SymbolTable`
  - [ ] Unqualified-name lookup in local scopes (calc parameters, state variables, enclosing definitions)
  - [ ] Qualified-name lookup against package namespaces and `LibrarySymbolIndex`
  - [ ] Emit `SemanticIssue(error)` for unresolved expression identifiers

---

## Recently Completed

- [x] **Phase A (v0.53.1):** Grammar Class Integrity & 100% Parse Conformance
  - [x] `get_definition()` added to all 36 missing classes (reflection audit: 358/358)
  - [x] `ReturnParameterMember` list-vs-dict round-trip bug fixed
  - [x] `Import_Visibility_Valid.error` updated; XPect conformance 123/123 (100%)

---

## Upcoming Milestones

- [ ] **Phase C (v0.55.0):** Semantic expression type compatibility and unit safety checking
- [ ] **Phase D (v0.56.0+):** ANTLR SLL mode fast-path parsing & graph store query enhancements
