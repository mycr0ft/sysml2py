# sysmlpy — Master Development Plan & Roadmap

> **Current Version:** v0.55.0 (August 2026)  
> **Repository:** https://github.com/mycr0ft/sysmlpy  
> **Upstream Grammar PR:** [daltskin/sysml-v2-grammar#12](https://github.com/daltskin/sysml-v2-grammar/pull/12)

---

## 1. Executive Summary & Current State

`sysmlpy` is a Python library for parsing, manipulating, and validating SysML v2.0 models using an ANTLR4-based parser, a rich AST of grammar classes, and a semantic analysis engine.

### Current Health & Metrics (v0.55.0)
- **Full Test Suite:** 836/836 passed (fast + grammar + XPect conformance).
- **Grammar Round-Trip Suite:** 143/143 passed (100%).
- **XPect Parse Conformance:** 123/123 (100%).
- **Grammar Class Integrity:** 358/358 classes implement `get_definition()` (reflection-audited in v0.53.1).
- **Expression Name Resolution:** Identifiers inside constraint bodies, calc results, attribute defaults, and guards resolve against the symbol table (v0.54.0).
- **Expression Type Safety:** Operand-category rules and pint unit-dimension checks emit `OPERAND_TYPE_MISMATCH` / `UNIT_DIMENSION_MISMATCH`; `const_fold()` reduces deterministic literals (v0.55.0).
- **Expression Engine:** Structured per-precedence capture now covers boolean keyword operators (`and`/`or`/`xor`/`implies`) and `**` exponentiation (previously glued text).
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
│ Phase D: High-Performance Parsing & Graph Store (v0.56.0+) ← NEXT       │
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

### Phase D: Storage Engine & Scale Optimizations (v0.56.0+) — NEXT

#### Goal
Now that expressions are captured as structured AST nodes rather than collapsed text strings, the semantic analyzer can walk expression trees and validate identifiers against the `SymbolTable`.

#### Design
1. **Expression AST Walker (`semantic.py`):**
   - Create `_walk_expression_identifiers(expr_dict)` to recursively traverse `OwnedExpression` chains.
   - At each `FeatureReferenceExpression` / `FeatureReferenceMember`, extract the target `QualifiedName`.
   - At each `FeatureChainMember`, record the base target and successive navigation steps (`wheel1.mass`).
2. **Symbol Resolution:**
   - Look up unqualified names in local scope (`CalculationUsage` parameters, `StateUsage` variables, enclosing `PartDefinition` attributes).
   - Look up qualified names against package namespaces and `LibrarySymbolIndex` (e.g. `ScalarValues::Real`, `ISQ::mass`).
3. **Diagnostics:**
   - Emit `SemanticIssue(severity="error", message=f"Unresolved identifier '{name}' in expression", element=...)`.
   - Track resolution status on the AST node.

---

### Phase C: Semantic Type Compatibility & Unit Safety (v0.55.0)

#### Goal
Verify type safety and unit consistency inside expressions.

#### Features
1. **Operator Type Checking:**
   - Arithmetic (`+`, `-`, `*`, `/`, `%`, `**`): operands must resolve to `ScalarValues::Real`, `ScalarValues::Integer`, or compatible unit dimensions.
   - Relational (`<`, `>`, `<=`, `>=`): operands must have ordered types.
   - Logical (`and`, `or`, `xor`, `implies`, `not`): operands must resolve to `ScalarValues::Boolean`.
   - Equality (`==`, `!=`): operands must have compatible classifier types.
2. **Unit Dimension Compatibility:**
   - Use `pint` integration to verify dimensional consistency (e.g. adding `[m]` to `[kg]` raises a dimensional mismatch error).
3. **Static Evaluation:**
   - Constant-fold deterministic literal expressions (e.g. `10 [kg] * 2` → `20 [kg]`).

---

### Phase D: Storage Engine & Scale Optimizations (v0.56.0+)

#### Goal
Optimize parsing throughput on large system models (10,000+ elements) and enhance graph query capabilities.

#### Features
1. **ANTLR Two-Stage Parsing (SLL → LL Fallback):**
   - Configure ANTLR `PredictionMode.SLL` for fast initial parsing, falling back to full `PredictionMode.LL` only on syntax ambiguity. Significantly accelerates large file parsing.
2. **Graph Backend Extensions:**
   - Support Cypher queries on `KuzuStore` for structural graph traversal.
   - Support path queries and centrality analysis on `NetworkXStore`.

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
