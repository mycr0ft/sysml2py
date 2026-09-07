# sysmlpy — TODO & Action Items

See the comprehensive [Master Development Plan](docs/archive/DEVELOPMENT_PLAN.md) for architectural roadmap, active development phases, and planned milestones.

See [STATUS.md](STATUS.md) and [CHANGELOG.md](CHANGELOG.md) for the current project status and release history.

---

## Active Tasks (Post-Phase-D candidates)

Phases A–D from the [Master Development Plan](docs/archive/DEVELOPMENT_PLAN.md)
are complete.  Follow-up work is organized under the
[Adoption Roadmap](docs/archive/DEVELOPMENT_PLAN.md#6-adoption-roadmap-v061--making-sysmlpy-useful-to-systems-engineers)
(§6 of the plan) — goals to make sysmlpy useful to systems engineers:

- [x] **Goal 1 — CLI: `analyze` + `view` commands with exit codes** *(v0.61.0: `sysmlpy analyze FILE... [--format json] [--fail-on ...]`, `sysmlpy view FILE --view NAME [--focus ...] [-o ...]`, `parse`/`format` subcommands, documented 0/1/2 exit codes, legacy flat form preserved; 39 tests in `tests/cli_test.py`)*
- [x] **Goal 2 — Requirement traceability & verification coverage** *(v0.62.0: `verification def`/`verification` usages and `verify` members (reference + inline declaration forms) parse and round-trip; `Requirement.subject`/`.verified_by` extraction; new `sysmlpy.traceability` module with `extract_traceability` → `TraceabilityReport` (coverage queries, text/markdown/json output) and `as_traceability_matrix_view` (markdown/html/plantuml); `sysmlpy trace` CLI with `--fail-on uncovered` exit gate; 46 tests in `tests/traceability_test.py`)*
- [x] **Goal 3 — JSON interchange format** *(v0.63.0: `sysmlpy.interchange` module — `to_interchange()` / `from_interchange()` JSON-LD-style partition documents (flat `@graph`, `@id`/`@type` elements, deterministic uuid5 ids); lossless import back to a live model via the shared `Model._load_definition()` path; `sysmlpy export` / `sysmlpy import` CLI commands; 38 tests in `tests/interchange_test.py`. Spec-normative JSON-LD context mapping (OMG property IRIs) tracked as follow-up.)*
- [x] **Goal 4 — Expression evaluator** *(v0.64.0: `sysmlpy.evaluator` — `collect_values()` / `evaluate_expression()` / `evaluate_calculation()` / `check_constraints()`; pint attribute values bind into calc/constraint evaluation with what-if `bindings`; feature-chain resolution with type fallback; glued unit-expression handling; `sysmlpy eval` CLI with `--expr`/`--set`/`--constraints`; calc defs inside part bodies no longer dropped by the visitor/object tree; 44 tests in `tests/evaluator_test.py`. Conditional expressions and calc `in` parameters tracked as follow-up.)*
- [x] **Goal 5 — LSP server** *(v0.65.0: `sysmlpy.lsp` package — dependency-free LSP 3.17 subset over stdio JSON-RPC; `publishDiagnostics` (exact ANTLR syntax ranges + `analyze()` issues located via quoted-name heuristic), `documentSymbol` outline, `hover` (kind/type/value), `definition` (usage→decl, type name→type def), keyword+member `completion`, FULL text sync, UTF-16 positions; `sysmlpy-lsp` console script + `python -m sysmlpy.lsp`; VS Code extension scaffold `editors/vscode/sysmlpy-lsp/`; Neovim recipes in `docs/LSP.md`; 37 tests in `tests/lsp_test.py`. Follow-ups: incremental sync, position-tracked semantic diagnostics, workspace/symbol, `.`-completion.)*
- [~] **Goal 6 — Rendering without Java** (native SVG / Mermaid output; boxes covers state
    machines, interconnection and action flows)
  - [x] **Phase 2 (v0.68.0)** — boxes-backed iv + afv: `as_interconnection_view_boxes()`
    (parts as boxes, boundary ports via `label_inside`, port-to-port Z-routed connection
    edges) and `as_action_flow_view_boxes()` (actions as boxes, parameters as in/out ports,
    flows port-to-port, nested actions as composite children, successions as dashed `..>`
    edges) against `diagramboxes` (renamed from `boxes`, v0.4.0 nested-node layout).
    Relationship legends now opt-in (`include_legend=False` default) — standard-notation
    legends were noise; monochrome `bw` stays the default style (color-vision
    accessibility); the dedicated palette option shipped in v0.69.0
    (`set_stereotype_palette("okabe-ito")`, see Goal 6).
  - [x] **sim: transition `do` effects live** (v0.69.0) — visitor
    emits `EffectBehaviorUsage` (reference form round-trips) plus
    readable `text` for send/accept/assignment forms; assignment
    effects render `target := value`.
  - [x] **sim: composite-state regions** (v0.69.0) — regions expand
    flat with qualified names (`Composite.Sub`, nesting supported):
    entering a composite lands in its initial substate, region
    transitions run inside, transitions declared on the composite
    apply from every substate (UML composite transitions, deeper
    transitions win the fall-through); parallel regions raise.
  - [x] **Goal 6: colorblind-safe palette** — `set_stereotype_palette("okabe-ito")`
    switches `style="color"` views to the Okabe-Ito palette; `bw`
    default unchanged.
  - [x] **sim follow-ups** — history/deep-history pseudostates and
    executing assignment effects via `set_value` shipped in v0.81.0;
    parallel regions (``state def C parallel { ... }``, root-level or
    nested) shipped in v0.89.0 — co-active regions with per-region
    transition dispatch, cross-region moves, and composite exits
    (``sim.state`` becomes a tuple of active leaves).
  - [x] **Phase 2d (unreleased)** — package view namespace enclosure
    (pilot `VStructure.casePackage`): packages render as
    `package "Name" { members }` with owned members nested inside;
    definitions as leaf boxes (no feature explosion); containment by
    enclosure only; typing/specialization arrows kept between members
    (unlabeled — typing sits in `name : Type` labels).
  - [x] **Phase 2c (unreleased)** — iv notation fidelity: enclosure
    nesting (no `*--` composition edges), typed usage labels
    (`s : Sensor`, no `--:|>` arrows), consumed definitions dropped
    with ports inherited onto usages as boundary boxes, flows and
    connections as the only edges (flows now port-to-port — flow-end
    chains recovered from FlowRedefinition; declared flow names
    restored from `Identification.declaredName`), `_extract_connections`
    wired in (thick plain connector lines). Afv verified unchanged.
  - [x] **Phase 2b (unreleased)** — afv control nodes in both renderers:
    PlantUML afv uses hexagons for decide/merge/fork/join (PlantUML
    deployment syntax has no diamond element; state-diagram `<<choice>>`
    pseudo-states cannot coexist with `*--`/`--:|>` arrows); boxes afv
    uses true **diamonds** (diagramboxes `DecisionNode`, parented in
    composites), start dots and done bullseyes, dashed guard-labeled
    chain edges. diagramboxes 0.5.0: obstacle-aware port routing —
    sugiyama port edges wrap around node bodies through free bands
    instead of cutting through them; single-ported edges anchor at
    the port boundary.
  - [x] **Phase 1 (v0.67.0)** — PlantUML notation fidelity: edge encodings aligned to the OMG pilot
    (thick plain connections, heaviest bindings, `--:|>` typing, `--||>` redefinition, send/accept
    actions, variant/objective/metadata, succession flow); connection endpoints now parse (visitor
    stub fixed); gv `auto_include_connections` edges; stv nested composite-state blocks; legends
    updated. Ground truth: OMG pilot PlantUML generator + official Graphical Notation figures;
    research corpus at `~/research/notation_corpus/` (NOTATION_RESEARCH.md). Next: boxes engine
    (rename pending — PyPI name collision) for Java-free SVG/braille; traceability matrix md/html
    already exists in `traceability.py`.
- [x] **Goal 7 — Spreadsheet bridge** *(v0.66.0: `sysmlpy.spreadsheet` — CSV export of tabular/data-value/matrix views (`output_format="csv"`, `view --format csv`), `write_xlsx()` workbook export + `sysmlpy xlsx` CLI (optional `openpyxl` extra `sysmlpy[xlsx]`), value import into evaluator bindings (`import_values_csv()`/`import_values_xlsx()`, `eval --set-file`, `parse_value_literal()`); 37 tests in `tests/spreadsheet_test.py`.)*
- [~] **Goal 8 — Semantic model diff** (review workflows)
  - [x] **Batch 1 (v0.74.0): element-level diff** — `sysmlpy.diff`:
    `diff_models()` / `diff_files()` with `(kind, qualified name)`
    identity, Def/Usage kind suffix, field-level changes (typing,
    subject, doc), text/Markdown/JSON rendering, `sysmlpy diff` CLI
    (CI exit codes).  Model UUIDs excluded; renames surface as
    removed+added pairs.
  - [x] **Batch 2 candidates** — all shipped as "Batch 3 — diff batch 2
    (v0.82.0)" (see below): rename detection (kind + structural-signature
    unique-candidate match), grammar-level fields (value, multiplicity,
    direction, abstract), state-machine diff via sim's `MachineDescriptor`,
    requirement trace edges, and the `--threshold` change-rate gate.
- [~] **Goal 9 — Validator depth** (more OCL well-formedness checks)
  - [x] **Batch 1 (v0.69.0): state machines** — `UNRESOLVED_TRANSITION_ENDPOINT`
    (error), `NO_INITIAL_STATE` (warning), `UNREACHABLE_STATE`
    (warning); run on the simulator's expanded descriptor so
    composite semantics are shared with `sysmlpy sim`.
  - [x] **Batch 2 (v0.69.1): triggers + requirements** —
    `UNRESOLVED_TRIGGER_PAYLOAD` (error; bare + guarded `accept`
    forms) and `REQUIREMENT_UNCOVERED` (warning; requirement usages
    only, defs exempt).  Also fixed an `UnboundLocalError` crash in
    `analyze()` when the optional `sim` extra is absent.
  - [x] **Batch 3 (v0.70.0): trace targets** —
    `UNRESOLVED_TRACE_TARGET` (error) and `TRACE_TARGET_NOT_REQUIREMENT`
    (warning) on `satisfy <req> by <part>` targets; exposes the Goal 2
    extractor's phantom-requirement behavior for dangling edges.
  - [x] **Batch 4 (v0.71.0): verify + directions** —
    `UNRESOLVED_VERIFY_TARGET` (error; verify members inside
    requirements) and `CONNECTOR_DIRECTION_MISMATCH` (warning;
    same-direction port wiring, scoped end resolution).  The visitor
    drops verify members' `: VC` typing (fsp empty) — noted.
  - [x] **Batch 5 (v0.72.0)** — nested-satisfy coverage bug fix
    (false REQUIREMENT_UNCOVERED), `UNRESOLVED_SATISFY_PART` (error),
    deep feature-chain ends (>=3 segments) in direction checks.
  - [x] **Batch 6 (v0.73.0)** — `UNRESOLVED_CONNECTOR_END` (error;
    conservative resolution with library/subclass skips), chains
    through port typings (`a.p1.bus.pb`), `SATISFY_SUBJECT_TYPE_MISMATCH`
    (warning; subject vs by-part inheritance walk).  Abstract-typing
    warnings **dropped by design**: typing by abstract defs is valid
    SysML v2 — flagging would be a false positive by construction.
- [x] **Goal 9 — Validator depth** complete after 6 batches (v0.69.0 –
  v0.73.0): 29 rule codes total.
- [x] **Goal 10 — Technical stubs** (connector-end compatibility, `*`/`/` unit derivation, SLL error parity, regex→parser library extraction, Cayley parity) — closed v0.77.0; query-surface parity across NetworkX/Kùzu/Cayley finished v0.86.0
  - [x] **Batch 1 (v0.75.0): `*`/`/` unit-dimension derivation** —
    `UNIT_DIMENSION_DERIVATION_MISMATCH` (error, rule code 30):
    initializer dimension derived algebraically (`*` adds, `/`
    subtracts, literal `**` multiplies exponents) and compared with
    the declared quantity type; conservative skips for unknown
    operands / bare literals / `%` / boolean levels.  Plus SLL error
    parity: `prediction_mode="sll_only"` keeps the fallback pass in
    SLL prediction (previously stage 2 silently ran LL).
  - [x] **Batch 2 (v0.76.0): connector-end type compatibility** —
    `CONNECTOR_END_TYPE_MISMATCH` (warning, rule code 31): both ends
    local `port def` typings, unrelated by (transitive)
    specialization -> flag; chained ends, library typings and
    part-to-part ends skipped.  Supersedes the old `pass` stub.
  - [x] **Batch 2 (v0.76.0): regex→parser import extraction** —
    `_extract_imports` scans the lexer token stream: bare imports
    extracted (missed by the regex), comment/string false positives
    gone, syntax-error tolerant.
  - [x] **Batch 3 (v0.77.0): CayleyStore hardening + query parity**
    — verified against a live podman Cayley v0.7 server: fixed
    `clear()` stub, `_delete_quads` posting to /write instead of
    /delete, `delete()` no-op, `get()` marker/edge leaks, `put()`
    overwrite, `__len__` whole-DB count, no-filter query shape,
    `subgraph()` self-edges; glob query parity with NetworkX
    (client-side fnmatch); label-namespaced subjects so multiple
    stores can share a server.  **Goal 10 complete.**

- [~] **Goal 11 — Polish & follow-through** (the assorted-fixes umbrella;
  batched from the follow-ups scattered across this file)
  - [x] **Batch 1 (v0.79.0): model semantics** — `Model.resolve_types()`
    links `typed_by_name` to definition objects (`typedby`/`ref_type`)
    model-wide (simple, `::`-qualified and relative-qualified names;
    library/unresolved skipped; package-scoped ambiguity rule);
    serialization-safe typedby insertion (`_typedby_serialized_elsewhere`
    guard — parsed/resolved models dump byte-identically, standalone
    programmatic wiring still hoists); `Model.load` sets package
    parents.  CayleyStore query extensions: `all_paths`,
    `in_degree_centrality`, `out_degree_centrality`,
    `descendants_depth_limited`, `neighborhood`, `impact_analysis`,
    `siblings`, `hub_elements`, `shortest_path_between_named`
    (client-side gizmo; NetworkX/Kuzu shape parity).
  - [x] **Follow-up feature (v0.80.0): constraint textual bodies** —
    `rep language "..." /* ... */` kept in constraint/calc bodies and
    exposed via `Constraint.body_text`/`body_language`; unparsable
    natural-language constraint bodies salvaged by the parser rescue
    pass (rescue_language param, UserWarning per salvage) instead of
    failing the model; check_constraints reports them as
    non-evaluable.  Constraint name extraction fixed (declaration
    walk).  Conditional-expression *evaluation* still open (below).
  - [x] **Follow-up fix (v0.79.1): `ref` usages in the object tree** —
    package-level refs (visitor dispatch) and nested refs (class
    dispatch) were silently dropped; new `Reference.load_from_grammar`
    (+ `usage_dump`) preserves name/typing/redefinition, byte-identical
    round-trips; `Reference.__init__` now initializes base-Usage state.
  - [x] **Batch 2 — sim (v0.81.0)**: executing assignment effects via
    `set_value` (`do x := <expr>` evaluated + applied, recorded on
    `StepRecord.assignments`; failures logged, never fatal);
    history/deep-history pseudostates (`HistoryUsage` typing or
    `h;`/`history;` name convention; shallow default,
    `deep_history=True` option + `sysmlpy sim --deep-history`; region
    default entry as the no-history fallback).  Parallel regions
    still raise (by design, for now).
  - [x] **Batch 3 — diff batch 2 (v0.82.0)**: rename detection
    (kind + structural-signature unique-candidate match; ambiguous
    stays removed+added); grammar-level signature fields (value,
    multiplicity, direction, abstract — canonical-dump heuristics);
    state-machine diff via sim's MachineDescriptor
    (`diff_state_machines`); requirement trace edges (`traces`
    signature field via extract_traceability); `--threshold`
    change-rate gate (CLI + `ModelDiff.change_rate`).  Also fixed
    Requirement/Interface/Message base-Usage init (redefinition
    loads crashed).
  - [x] **Batch 4 — LSP (v0.83.0)**: incremental sync (ranged
    `didChange` edits, UTF-16, full-text still accepted);
    position-tracked semantic diagnostics via source-order pairing
    (element ↔ *n*-th declaration occurrence, `def` preferred for
    definitions); `workspace/symbol` (open docs + root `*.sysml`
    scan, cached); `.`-member completion via type names, falling
    back to the last good parse while the text is transiently
    broken.  Parser-side token positions remain future work.
  - [x] **Batch 5 — performance (v0.84.0)**: persistent DFA cache
    (`sysmlpy.dfa_cache`) — warmed parser/lexer ATN+DFA+prediction-
    context graphs pickled after the first parse, reinstated on cold
    start (cold 8–10 s → ~2.9 s on the 27 KB benchmark model, 3.7x;
    identity rebinds for `PredictionContext.EMPTY` /
    `SemanticContext.NONE` copies on load; cache failures fall back to
    normal parsing).  Visitor profiling harness (`benchmarks/
    profile_parse.py`) shows the ANTLR parse dominates ~80 % with no
    single visitor hotspot — micro-optimisation not pursued.
  - [x] **Batch 6 — interchange/evaluator (v0.85.0)**: spec-normative
    JSON-LD context mapping (`build_jsonld_context`, configurable
    vocabulary IRI); conditional expressions (``if c ? a else b``) and
    calc ``in`` parameters in the evaluator (positional invocation,
    declared defaults, recursion).

---

## Next Batch — v0.88.0: control-flow member fidelity + usage-body imports

Follow-ups surfaced by the v0.87.0 fidelity sweep, all verified against
the v0.87.0 tree on 2026-09-06 (fast suite 1484 passed / 2 skipped,
conformance 123/123).

- [x] **A1 — `accept` member name + typing silently dropped**
  (`action a1 { accept msg : M; }` dumps as `accept ;` — same silent-drop
  class as v0.79.1 `ref` / v0.87.0 filter-expose).  `_visit_payload_feature`
  (antlr_visitor.py) hardcodes `identification`/`pfsp` to None and only
  handles the `ownedFeatureTyping` alternative, but
  `payloadFeature : identification payloadFeatureSpecializationPart
  valuePart? | identification valuePart | ownedFeatureTyping …` —
  `accept msg : M` parses via the first alternative.  Add a
  `_build_pfsp_from_ctx` helper (PayloadFeatureSpecializationPart dict:
  ownedRelationship/ownedRelationship2/mp, reusing the per-spec
  FeatureSpecialization dict builders) and extract identification +
  pfsp + valuePart.  Grammar classes are already complete
  (`PayloadFeature`, `PayloadFeatureSpecializationPart` at
  classes.py:7225/7301).
- [x] **A2 — `satisfy` valuepart dropped on dump**
  (`satisfy s1 : R = 3;` dumps as `satisfy s1 : R ;`).  The satisfy
  emitter (antlr_visitor.py ~:2495) reads `vp.ownedExpression()` off the
  ValuePartContext, but `valuePart : featureValue` and
  `featureValue : (EQ | COLON_EQ | DEFAULT …) ownedExpression` — the
  expression sits one level down.  Replace the inline extraction with
  the existing `_visit_value_part()` helper (handles EQ/COLON_EQ/DEFAULT
  flags).  `SatisfyRequirementUsage` grammar class already parses +
  dumps `valuepart` (classes.py:5353).
- [x] **A3 — usage-body imports dropped**
  (`part p1 { private import Q::*; }` dumps as `part p1;` — imports are
  legal in every body per `definitionBodyItem : importRule | …`).
  `_visit_definition_body_item_dict` (antlr_visitor.py:9983) never
  checks `item_ctx.importRule()`; `DefinitionBodyItem` (classes.py:5089)
  has no `"Import"` dispatch.  Mirror the package-body handling
  (`_visit_import_rule_dict` at antlr_visitor.py:893).
- [x] **A4 — `metadata` usage not surfaced as a public-API object**
  (`metadata m1 : MD;` parses as a MetadataFeature annotating element;
  the model tree wraps the *definition* as a Metadata object and the
  usage vanishes — `find('m1')` fails).  Size the wiring during
  implementation; at minimum document the annotation semantics and make
  the usage navigable.
- [x] **A5 — nested `rendering` usage has no public-API object**
  (`part w { rendering r2 : E; }` dumps correctly — v0.87.0 visitor fix —
  but usage.py's nested walk never creates a `Rendering` child).
  Add a RenderingUsage dispatch to the nested usage walk.
- [x] Round-trip / API tests for each fix in `tests/grammar_test.py` /
      `tests/class_test.py`.

---

## Next Batch — v0.87.0: round-trip fidelity close-out

Theme: close the last known silent-drop round-trip gaps (the v0.79.1
`ref` lineage), fix two dump/crash warts, a test-hygiene item, and
bring the agent-facing docs back to reality.  All items verified
against the v0.86.0 tree on 2026-09-06 (fast suite 1472 passed,
2 skipped).

- [x] **A1 — View `filter` / `expose` members silently dropped**
  (last remaining silent-loss TODOs in the visitor; same class as the
  v0.79.1 `ref` fix — `view v { filter @e1; }` parses clean and dumps
  as `view v ;`)
  - [x] Visitor: emit `ElementFilterMember` dicts in
        `_visit_view_definition_body_dict` (antlr_visitor.py:9110) and
        `_visit_view_body_dict` (:9149), and `Expose` dicts (:9151);
        grammar rules `elementFilterMember : memberPrefix FILTER
        ownedExpression SEMI` and `expose : EXPOSE (membershipExpose |
        namespaceExpose) relationshipBody`
  - [x] Grammar: implement `ElementFilterMember` and `Expose`
        (classes.py:9762/:9777 are empty stubs, `dump()` returns `""`)
  - [x] `ViewDefinitionBody` gains the missing `"Expose"` dispatch
        (ViewBody already has it)
  - [x] Round-trip tests in `tests/grammar_test.py` (filter with and
        without memberPrefix; membership + namespace expose forms)
- [x] **A2 — `ConnectionUsage.dump()` wart** — `keyword2 = "connect\n"`
  hardcodes a newline and the `connection` keyword is emitted even
  when the declaration is nameless, so `connect c1[0..1] to c2[1];`
  round-trips as `connection  connect\n c1 [0..1] to c2 [1] ;`
  (valid but non-canonical).  Emit bare `connect <ends>` for nameless
  declarations; drop the `\n`.
- [x] **A3 — `RootNamespace` latent crash + KerML silent drop**
  (classes.py:79) — the `ElementFilterMember` branch `pass`es without
  binding `memberclass`, then `self.children.append(memberclass)` runs
  unconditionally → `UnboundLocalError` if ever hit; the KerML
  `NamespaceBodyElement` root silently discards all members.  Handle
  ElementFilterMember gracefully (v0.27.0 contract: warn + skip), and
  load KerML root members instead of dropping them.
- [x] **A4 — register the `conformance` pytest mark** in
  `pyproject.toml` (removes the `PytestUnknownMarkWarning` on every
  run)
- [x] **B5 — fix broken `docs/DEVELOPMENT_PLAN.md` links** (moved to
  `docs/archive/` in v0.78.0; root TODO.md ×4 + docs/PROJECT_SUMMARY.md
  still point at the old path)
- [x] **B6 — refresh `AGENTS.md`** — version 0.69.0 → current, 79 → 143
  grammar tests, test-file map missing `cli`/`traceability`/
  `interchange`/`evaluator`/`lsp`/`spreadsheet`/`dfa_cache`/`sim`/etc.
- [x] **B7 — refresh `STATUS.md` stale tables** — Known Issues:
  definition.py dead-code entry gone (single ActionUsage branch at
  :1143), PackageBodyElement `#!TODO` comment gone; Medium Priority:
  connection multiplicity ends round-trip, nested `:>>` in `return`
  works, connector-end compat shipped v0.76.0
- [x] **B8 — refresh `TODO.md` stale bits** — Goal 8 "Batch 2
  candidates" all shipped in v0.82.0; "Next release: v0.70.0" line;
  palette option done (Okabe-Ito, v0.69.0)
- [x] **C9 — remove tracked debug artifacts** — `temp.txt`,
  `tests/temp.txt`, `test_puml/*.png|.puml`


**Discovered during A1–A4 implementation (follow-ups, not this batch):**

- [x] Nested behavior-usage typings: `part p { action a1 : A; }` and
      friends — the nested behavior dispatch emitters
      (`_visit_nested_occurrence_usage`, `_visit_nested_usage`) still
      hardcode `specialization: None`; top-level and grammar-class dump
      paths are fixed (v0.87.0).  *(→ v0.88.1: verified empirically that
      the grammar rejects typed declarations on send/terminate/accept/
      assignment/message/binding/succession, so the None slots are
      unreachable — the one reachable case (transition usage typing) is
      fixed; `_visit_nested_usage` + 11 zero-call-site helpers deleted
      (410 lines).  Nested usages inside state bodies now surface via
      the full load path.)*
- [x] Nested `rendering r2 : E;` inside a part body dumps correctly but
      produces no public-API object; `metadata m1` also not findable
      via `find()` *(→ v0.88.0: Rendering child + Metadata child with
      name/typed_by_name; `MetadataFeature` accepted by
      `NonOccurrenceUsageElement` for rebuild round-trips)*
- [x] Usage-body imports dropped everywhere
      (`part p1 : E { private import Q::*; }`) — the visitor never
      dispatches `importRule` in `_visit_definition_body_item_dict` and
      `DefinitionBodyItem` has no Import branch *(→ v0.88.0: all
      visibility forms round-trip; bare `import` stays rejected —
      grammar-correct)*
- [x] `satisfy` valuepart dropped on dump (`satisfy R = 3;` loads, but
      the visitor emits a `"valuepart"` key ~antlr_visitor.py:2521 that
      the grammar class ignores) *(→ v0.88.0: emitter now uses the
      shared `_visit_value_part` helper; EQ/COLON_EQ/DEFAULT preserved)*

---

Legacy candidate follow-up work:

- [x] `*`/`/` unit-dimension derivation (`mass * speed` vs `ForceValue`) *(→ Goal 10, v0.75.0)*
- [x] SLL error-message parity (align ANTLR wording between prediction modes) *(→ Goal 10, v0.75.0)*
- [x] Persistent DFA cache serialization to eliminate cold-start parse cost *(→ Batch 5, v0.84.0)*
- [x] Visitor performance profiling (`parse_to_dict` dominates end-to-end time) *(→ Batch 5, v0.84.0 — no visitor hotspot found; parse dominates)*
- [x] CayleyStore query extensions (parity with NetworkX/Kùzu) *(→ Goal 10, closed v0.86.0 — identical query surface + parity test on NetworkX/Kùzu/Cayley)*
- [x] Spec-normative JSON-LD context mapping (OMG property IRIs) *(→ Batch 6, v0.85.0)*
- [x] Conditional expressions and calc `in` parameters in the evaluator *(→ Batch 6, v0.85.0)*

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

- (none — Phase D is the final planned phase; see docs/archive/DEVELOPMENT_PLAN.md)
