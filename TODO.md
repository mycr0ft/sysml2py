# sysmlpy — TODO & Action Items

See the comprehensive [Master Development Plan](docs/DEVELOPMENT_PLAN.md) for architectural roadmap, active development phases, and planned milestones.

See [STATUS.md](STATUS.md) and [CHANGELOG.md](CHANGELOG.md) for the current project status and release history.

---

## Active Tasks (Phase A: v0.53.1)

- [ ] **Grammar Class `get_definition()` Completeness:**
  - [ ] Add `AdditiveOperand.get_definition()` in `src/sysmlpy/grammar/classes.py`
  - [ ] Add `AssignmentNode.get_definition()` in `src/sysmlpy/grammar/classes.py`
  - [ ] Add `TriggerValuePart.get_definition()`, `TriggerFeatureValue.get_definition()`, `TriggerExpression.get_definition()`
  - [ ] Run reflection audit across all ~354 grammar classes to ensure zero missing `get_definition()` or `children` implementations
- [ ] **XPect Conformance Suite:**
  - [ ] Update `tests/sysmlv2/validation/valid/Import_Visibility_Valid.error` to match the expected syntax error on bare import
  - [ ] Verify 123/123 (100%) passing conformance suite

---

## Upcoming Milestones

- [ ] **Phase B (v0.54.0):** Name resolution on structured expressions (`assert constraint`, `calc`, `constraint`, `default value`)
- [ ] **Phase C (v0.55.0):** Semantic expression type compatibility and unit safety checking
- [ ] **Phase D (v0.56.0+):** ANTLR SLL mode fast-path parsing & graph store query enhancements
