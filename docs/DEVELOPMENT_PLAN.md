# sysmlpy — Master Development Plan & Roadmap

> **Current Version:** v0.59.0 (August 2026)  
> **Repository:** https://github.com/mycr0ft/sysmlpy  
> **Upstream Grammar PR:** [daltskin/sysml-v2-grammar#12](https://github.com/daltskin/sysml-v2-grammar/pull/12)

---

## 1. Executive Summary & Current State

`sysmlpy` is a Python library for parsing, manipulating, and validating SysML v2.0 models using an ANTLR4-based parser, a rich AST of grammar classes, and a semantic analysis engine.

### Current Health & Metrics (v0.56.0)
- **Full Test Suite:** 809 fast-suite + 123 XPect conformance pass (932 total, 0 failures).
- **Grammar Round-Trip Suite:** 143/143 passed (100%).
- **XPect Parse Conformance:** 123/123 (100%).
- **Grammar Class Integrity:** 358/358 classes implement `get_definition()` (reflection-audited in v0.53.1).
- **Expression Validation Pipeline:** name resolution (v0.54.0) → operand-type rules + unit-dimension safety + `const_fold()` (v0.55.0).
- **Parsing Performance:** two-stage SLL → LL — parse-only **38 % faster** (4.92 s vs 7.89 s on a 6,000-element model, warmed), identical error positions on fallback (v0.56.0).
- **Graph Queries:** NetworkX path/impact/degree extensions; Kùzu raw Cypher passthrough with named-path/sibling/hub queries (v0.56.0).
- **Upstream Grammar Conformance:** 310/310 official OMG specification fixture files parse cleanly via the corrected grammar in `daltskin/sysml-v2-grammar#12`.

---

## 2. Recent Major Milestones Completed

### Phase 0: AST Usage Propagation (v0.48.0)
- All usage kinds (`assert constraint`, `constraint`, `calc`, `state`, `action`, `requirement`, `satisfy`, `allocation`) inside `part def` / `item def` bodies now survive `Part.load_from_grammar` into the public-API model tree.

### Phase 1: Per-Precedence Grammar & Cascade Emission (v0.52.0 – v0.53.0)
- Upstream ANTLR grammar rewritten with a 13-tier operator precedence cascade (`nullCoalescing` → `implies` → `or` → `xor` → `and` → `equality` → `classification` → `relational` → `range` → `additive` → `multiplicative` → `exponentiation` → `unary`), aligned with the OMG XText reference grammar (`KerMLExpressions.xtext`).
- Logical operator ordering aligned: `and` binds tighter than `xor` (`a xor b and c` = `a xor (b and c)`).
- Visitor rewritten to walk the grammar cascade directly, populating structured layer dictionaries for downstream analysis.
- Postfix operators (`meta`, `@@`, `@`) and `all` extent expressions restored at correct precedence.
- Import visibility rules aligned with normative OMG spec (explicit visibility required).

### Phase A: Grammar Class Integrity & 100% Parse Conformance (v0.53.1) ✅
- `get_definition()` added to the final 36 missing grammar classes (reflection audit: 358/358 complete), including `AssignmentNode`, `AdditiveOperand`, the `Trigger*` family, and the expression-member chain.
- Fixed `ReturnParameterMember.get_definition()` list-vs-dict shape bug that broke `loads()` on calc `return` members.
- XPect conformance reached 123/123 by updating `Import_Visibility_Valid.error` to expect the enforced bare-import syntax error.

---

## 3. Active & Upcoming Development Phases

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Phase A: Grammar Class Integrity & 100% Conformance Suite (v0.53.1) ✅  │
│   - Fix missing get_definition() across all ~354 grammar classes       │
│   - Bring 123-file XPect parse conformance to 100%                     │
└────────────────────────────────────┬─────────────────────────────────────┘
                                     │
┌────────────────────────────────────▼─────────────────────────────────────┐
│ Phase B: Name Resolution on Structured Expressions (v0.54.0) ✅         │
│   - Resolve FeatureReferenceExpression / FeatureChain against SymbolTable│
│   - Identify unbound variables, scoped attributes, and imported symbols  │
│   - Emit SemanticIssues for unresolved expression identifiers            │
└────────────────────────────────────┬─────────────────────────────────────┘
                                     │
┌────────────────────────────────────▼─────────────────────────────────────┐
│ Phase C: Expression Type Checking & Static Evaluation (v0.55.0) ✅      │
│   - Operator operand type compatibility (numeric, boolean, string)       │
│   - Pint unit compatibility checking inside expressions                  │
│   - Constant folding / static expression reduction                       │
└────────────────────────────────────┬─────────────────────────────────────┘
                                     │
┌────────────────────────────────────▼─────────────────────────────────────┐
│ Phase D: High-Performance Parsing & Graph Store (v0.56.0) ✅            │
│   - ANTLR SLL fast-path prediction optimization for large models         │
│   - NetworkX and Kùzu graph query extensions                             │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Detailed Phase Specifications

### Phase A: Grammar Class Integrity & 100% Parse Conformance (COMPLETE / v0.53.1)

#### Resolution
All items complete as of v0.53.1:
- `get_definition()` added to all 36 missing classes (audit found more than the 5 originally identified). Full list in `CHANGELOG.md` v0.53.1.
- Reflection audit confirms **358/358** classes implement `get_definition()`.
- `ReturnParameterMember.get_definition()` shape bug fixed (list vs dict for `ownedRelatedElement`).
- `Import_Visibility_Valid.error` updated to the enforced bare-import syntax error; **XPect conformance 123/123 (100%)**.

### Phase B: Name Resolution on Structured Expressions (COMPLETE / v0.54.0)

#### Resolution
Implemented as analyzer step 4b (`SemanticAnalyzer._check_expression_identifiers`):
- `ExpressionIdentifierCollector` walks the public-API model tree and extracts identifiers from each expression-owning element's grammar (`constraint`, `assert constraint`, `calc`, attribute/item/port/reference defaults, transition guards).
- `_walk_expression_identifiers()` traverses the v0.52 per-precedence expression dict (Conditional → … → Primary), pulling QualifiedNames from `FeatureReferenceMember`, `PrimaryExpression` base + `ownedRelationship1/2` chains, `OwnedFeatureChain` steps, and `InvocationExpression` targets/arguments.
- `SemanticIssue(severity="error", code="UNRESOLVED_EXPRESSION_IDENTIFIER")` emitted for unresolved names; dotted chains resolve segment-by-segment (`_resolve_feature_chain`).
- Library fix bundled in: `function` declarations now indexed (~1604 symbols, up from ~1417) and the bundled library is the default `lib_roots` so `size()` etc. resolve without explicit `library=`.

### Phase C: Semantic Type Compatibility & Unit Safety (COMPLETE / v0.55.0)

#### Resolution
Implemented as analyzer step 4c (`SemanticAnalyzer._check_expression_types`) backed by
`ExpressionTypeChecker`:
- `_Operand` classification (literal int/float/string/bool, typed by declared type, invocation, chain, unknown) resolving identifiers via the Phase B scope machinery.
- Operator rules → `OPERAND_TYPE_MISMATCH`: logical (boolean required), relational (ordered required), equality (bool vs non-bool), arithmetic (string/boolean mismatches), unary `not`/`-`.
- Unit checking → `UNIT_DIMENSION_MISMATCH` for `+`/`-` across different ISQ dimensions; dimensions parsed from the bundled library's `quantity dimension:` annotations (alias-aware, ~560 types).
- `const_fold()` static reduction including a restricted AST-evaluator for parenthesized text arithmetic (`-(2-5)` → 3).
- Prerequisite: structured emission of boolean keyword operators (`and`/`or`/`xor`/`implies`) and `**` exponentiation with `LiteralBoolean` primaries; grammar classes round-trip them.

### Phase D: Storage Engine & Scale Optimizations — Legacy Design Note (SUPERSEDED by the COMPLETE section below)

(Original Phase B design notes retained for history — see the v0.54.0 changelog for the delivered implementation.)

---

### Phase C: Semantic Type Compatibility & Unit Safety — Legacy Design Note (SUPERSEDED by the COMPLETE section above)

#### Original Goal (v0.55.0 — delivered)
Operator type rules, pint unit-dimension checks, and constant folding — all delivered; see the v0.55.0 changelog and the COMPLETE section above.

---

### Phase D: Storage Engine & Scale Optimizations (COMPLETE / v0.56.0)

#### Resolution
Implemented in v0.56.0:
- **Two-stage parsing** (`antlr_parser.py`): SLL `BailErrorStrategy` fast path; on
  any failure the source is re-parsed once under full LL with the default error
  strategy — identical trees for valid input, identical error *positions* for
  invalid input.  `prediction_mode=` parameter (`sll` default / `ll` / `sll_only`).
- **NetworkX extensions**: `all_paths` (capped simple-path enumeration),
  `descendants_depth_limited`, `neighborhood` (ego graph), `impact analysis`
  (transitive down/upstream), `in_degree_centrality` / `out_degree_centrality`.
- **Kùzu extensions**: `execute_cypher` (raw passthrough with node flattening),
  `shortest_path_between_named` (hop-expanding; Kùzu lacks `shortestPath()`),
  `siblings`, `hub_elements` (outgoing/incoming/both degree hubs).

---
## Project Plan Complete

All four planned phases (A–D) are implemented.  Follow-up candidates are
tracked in [TODO.md](../TODO.md).  Post-plan high-priority fixes:

- **v0.57.0 — Typed-by preservation:** `_extract_specialization_info()`
  hoisted to base `Usage` and extended to both grammar layouts; new
  `Usage.typed_by_name` property populated on `loads()` for all usage
  kinds.  Follow-up: resolve `typedby` to the definition object.
- **v0.58.0 — Import/AliasMember order:** both `_ensure_body()` paths
  (Model + Package) preserve source positions of imports and aliases;
  interleaved files now round-trip exactly through `loads().dump()`.
- **v0.59.0 — Top-level multiplicity:** bounds verified fixed since
  v0.40.0 (stale docs cleared); the residual `ordered` / `nonunique`
  flag bugs (visitor extractors hardcoded `False`, `MultiplicityPart.dump()`
  XOR-guard) fixed in v0.59.0.  All STATUS.md High Priority items done.

---

## 5. Testing & Verification Standard

Before merging any changes or cutting a release:
1. **Fast Suite:**
   ```bash
   poetry run pytest tests/ -m "not conformance" --tb=short -q
   ```
   *Requirement: 0 failures, 0 errors.*
2. **Grammar Round-Trip:**
   ```bash
   poetry run pytest tests/grammar_test.py --tb=short -q
   ```
   *Requirement: 143/143 passed.*
3. **Conformance Suite:**
   ```bash
   poetry run pytest -m conformance --tb=short -q
   ```
   *Requirement: 123/123 passed.*
4. **Upstream Grammar Synchronization:**
   ```bash
   cd ~/sysml-v2-grammar && python3 scripts/conformance.py --verbose
   ```
   *Requirement: 310/310 official fixture files passed.*
