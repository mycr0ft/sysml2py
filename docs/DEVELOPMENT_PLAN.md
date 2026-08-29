# sysmlpy — Master Development Plan & Roadmap

> **Current Version:** v0.53.0 (August 2026)  
> **Repository:** https://github.com/mycr0ft/sysmlpy  
> **Upstream Grammar PR:** [daltskin/sysml-v2-grammar#12](https://github.com/daltskin/sysml-v2-grammar/pull/12)

---

## 1. Executive Summary & Current State

`sysmlpy` is a Python library for parsing, manipulating, and validating SysML v2.0 models using an ANTLR4-based parser, a rich AST of grammar classes, and a semantic analysis engine.

### Current Health & Metrics (v0.53.0)
- **Fast Test Suite:** 684/684 passed (100%) across grammar round-trips, public API classes, navigation, semantic analysis, import resolution, and PlantUML renderings.
- **Grammar Round-Trip Suite:** 143/143 passed (100%).
- **Upstream Grammar Conformance:** 310/310 official OMG specification fixture files parse cleanly via the corrected grammar in `daltskin/sysml-v2-grammar#12`.
- **Expression Engine:** Structured, per-precedence AST capture active for binary, unary, invocation, and feature-chain expressions (replacing legacy collapse-to-text).

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

---

## 3. Active & Upcoming Development Phases

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Phase A: Grammar Class Integrity & 100% Conformance Suite (v0.53.1)      │
│   - Fix missing get_definition() across all ~354 grammar classes         │
│   - Bring 123-file XPect parse conformance to 100%                       │
└────────────────────────────────────┬─────────────────────────────────────┘
                                     │
┌────────────────────────────────────▼─────────────────────────────────────┐
│ Phase B: Name Resolution on Structured Expressions (v0.54.0)             │
│   - Resolve FeatureReferenceExpression / FeatureChain against SymbolTable│
│   - Identify unbound variables, scoped attributes, and imported symbols  │
│   - Emit SemanticIssues for unresolved expression identifiers            │
└────────────────────────────────────┬─────────────────────────────────────┘
                                     │
┌────────────────────────────────────▼─────────────────────────────────────┐
│ Phase C: Expression Type Checking & Static Evaluation (v0.55.0)          │
│   - Operator operand type compatibility (numeric, boolean, string)       │
│   - Pint unit compatibility checking inside expressions                  │
│   - Constant folding / static expression reduction                       │
└────────────────────────────────────┬─────────────────────────────────────┘
                                     │
┌────────────────────────────────────▼─────────────────────────────────────┐
│ Phase D: High-Performance Parsing & Graph Store Integration (v0.56.0+)   │
│   - ANTLR SLL fast-path prediction optimization for large models         │
│   - NetworkX and Kùzu graph query extensions                             │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Detailed Phase Specifications

### Phase A: Grammar Class Integrity & 100% Parse Conformance (Immediate / v0.53.1)

#### Problem
In `src/sysmlpy/grammar/classes.py`, certain grammar classes implement `__init__` and `dump()` but lack `get_definition()`. When `loads()` or `_ensure_body()` serializes the grammar tree, missing methods cause `AttributeError: '<Class>' object has no attribute 'get_definition'`.

#### Identified Targets
1. **`AdditiveOperand`** (`src/sysmlpy/grammar/classes.py:5925`):
   ```python
   def get_definition(self):
       return {
           "name": self.__class__.__name__,
           "operator": self.operator,
           "operand": self.operand.get_definition(),
       }
   ```
2. **`AssignmentNode`** (`src/sysmlpy/grammar/classes.py:1349`):
   ```python
   def get_definition(self):
       return {
           "name": self.__class__.__name__,
           "prefix": self.prefix.get_definition() if self.prefix else None,
           "declaration": self.declaration.get_definition() if self.declaration else None,
           "body": self.body.get_definition() if self.body else None,
       }
   ```
3. **`TriggerValuePart`**, **`TriggerFeatureValue`**, **`TriggerExpression`** (`src/sysmlpy/grammar/classes.py:2402-2460`):
   Add reciprocal `get_definition()` implementations for transition triggers.
4. **Comprehensive Class Audit:**
   Audit all ~354 classes in `src/sysmlpy/grammar/classes.py` via automated reflection to verify every class implements `get_definition()` and `children`.
5. **XPect Conformance Suite Verification:**
   Update `tests/sysmlv2/validation/valid/Import_Visibility_Valid.error` to match the expected syntax error on bare `import`, bringing the 123-file XPect suite to 123/123 (100%) passing.

---

### Phase B: Name Resolution on Structured Expressions (v0.54.0)

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
