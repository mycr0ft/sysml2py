# CHANGELOG

## v0.88.1 (2026-09-06)

**Visitor dead-code removal + nested-definition fidelity + API typing
cosmetics.**

1. *Dead code deleted* — `_visit_nested_usage` (zero call sites) plus 11
   more zero-reference helpers (`_visit_accept_action_usage`,
   `_get_usage_typed_by`, `_visit_nested_definition`, and the
   `_build_binary_chain`/`_splice_unary`/`_layer_rank`/... expression
   family): 410 lines.  The remaining 12 `"specialization": None` slots
   in the node-declaration emitters were verified empirically to be
   unreachable — the grammar rejects typed declarations on send /
   terminate / accept / assignment / message / binding / succession
   forms, so they are correct as written (kept, not deleted).
2. *Nested definitions no longer dropped* — `part p { state def X; }`
   (and 16 sibling kinds: action / requirement / use case / enum / view /
   viewpoint / concern / metadata / verification / case / analysis case /
   individual / rendering / allocation / connection / flow defs, plus
   nested dependencies) were silently dropped by the nested-definition
   dispatcher (7 of ~25 kinds covered); the dump lost them entirely.
   `_visit_nested_definition_element` now dispatches all the kinds the
   package-level dispatcher handles.
3. *Nested usages in state bodies surface* — `state s1 { action a1 : A; }`
   inside a part had no API object (State body walk only knew nested
   states); the full load path now runs, so nested actions carry name +
   typed_by_name and nested states keep their children
   (`part p { state s1 { state s2; } }` previously lost s2).
4. *Typed transitions* — `transition t1 : T first e1;` dropped `: T`
   on dump (hardcoded `specialization: None`); the typing now round-trips
   and carries on the Transition object as typed_by_name.
5. *Satisfy API typing* — satisfy members now carry typed_by_name from
   the fsp requirement typing.  Important semantic note discovered here:
   in the ors+fsp form (`satisfy s1 : R`) the member is **anonymous** —
   `s1` (ors) is the *requirement being satisfied* (the trace target),
   not the member's name.  An initial attempt to name the member from
   the ors was reverted: it made satisfy targets self-resolve in the
   validator (UNRESOLVED_TRACE_TARGET silently vanished) and produced
   double matches in find_one.  The declaration form
   (`satisfy requirement r1 { ... }`) keeps its declared name.

Fast suite 1501 passed / 2 skipped; conformance 123/123.

## v0.88.0 (2026-09-06)

**Control-flow member fidelity + usage-body imports.**

All four follow-ups surfaced by the v0.87.0 fidelity sweep, plus one
bonus API gap:

1. *Usage-body imports* (A3) — `part p1 { private import Q::*; }`
   dumped as `part p1;`.  `_visit_definition_body_item_dict` now
   dispatches `importRule` (the first `definitionBodyItem`
   alternative) and `DefinitionBodyItem` handles the `Import`
   relationship — the same dict shape package bodies use.  public /
   protected / recursive (`::*::**`) forms all round-trip.
2. *`satisfy` valuepart* (A2) — `satisfy s1 : R = 3;` dumped as
   `satisfy s1 : R ;`.  The emitter read `vp.ownedExpression()` off
   the ValuePartContext, but `valuePart : featureValue` puts the
   expression one level down; it now uses the shared
   `_visit_value_part()` helper (EQ / COLON_EQ / DEFAULT flags
   preserved).  The `by` subject form keeps working.
3. *`accept` member name + typing* (A1) — `action a1 { accept msg
   : M; }` dumped as `accept ;`.  `_visit_payload_feature`
   hardcoded `identification`/`pfsp` to None and only handled the
   `ownedFeatureTyping` alternative; it now extracts the
   identification, the payloadFeatureSpecializationPart (new
   `_build_pfsp_from_ctx`, sharing the
   `_feature_specialization_dicts` core extracted from the usage
   builder) and the valuePart.  Multiplicity placement fixed in
   `PayloadFeatureSpecializationPart.dump()` (natural source order
   `: M[1]` — the previous mp-first rendering produced `[1] : M`,
   which does not re-parse).
4. *Metadata usages navigable* (A4) — package-level
   `metadata m1 : MD;` (and `@m1 : MD` / `about` forms) parses into a
   MetadataFeature annotation the public-API tree silently dropped
   (`find('m1')` failed).  Package.load_from_grammar now surfaces it
   as a Metadata child with name + typed_by_name; `MetadataFeature`
   is also accepted by `NonOccurrenceUsageElement` so the
   `_ensure_body` rebuild round-trips.
5. *Nested `rendering` usages* (A5) — `part w { rendering r2 : E; }`
   dumped correctly but produced no public-API object; the nested
   usage walk now creates a `Rendering` child (name + typed_by_name
   wired).

Fast suite 1493 passed / 2 skipped; conformance 123/123.

## v0.87.0 (2026-09-06)

**Round-trip fidelity close-out + view body members.**

*View `filter` / `expose` members (A1)* — the last known silent-drop
TODOs in the visitor (same class as the v0.79.1 `ref` fix):

1. *Visitor*: `_visit_view_definition_body_dict` and
   `_visit_view_body_dict` now emit `ElementFilterMember` dicts
   (``filter @e1;``) and `Expose` dicts (``expose e;`` /
   ``expose P::*;``) via new `_make_element_filter_member_dict` /
   `_make_expose_dict` helpers — previously a `pass  # TODO` stub,
   so views dumped as `view v ;`.
2. *Grammar classes*: `ElementFilterMember`, `Expose`,
   `MembershipExpose`, `NamespaceExpose` implemented (were empty
   stubs); `ViewDefinitionBody` gains the missing `"Expose"`
   dispatch; usage.py's View body walk tolerates payload-carrying
   members without their own model children.

*Other fixes:*

- **Guarded entry transitions** — `_visit_guarded_target_succession`
  probed nonexistent ctx attributes and emitted a dict shape the
  grammar class could not load (KeyError crash on
  ``entry a1; if x > 0 then s2;``). Rewritten to emit
  GuardExpressionMember + TransitionSuccessionMember; guarded entry
  now round-trips. Also fixed the two remaining undefined
  `_visit_expression` call sites (constraint member, satisfy visit).
- **`ConnectionUsage.dump()`** — bare `connect a to b;` no longer
  dumps as `connection  connect\n...`; typed-but-nameless
  connections (`connection : PressureSeat connect ...`) keep their
  typing.
- **`RootNamespace`** — KerML `NamespaceBodyElement` roots load their
  members (were silently dropped); a root-level `ElementFilterMember`
  warns + skips instead of raising `UnboundLocalError`.
- **Typing round-trip on prefixed usages** — the visitor emitters for
  view / viewpoint / concern / allocation / rendering / connection /
  individual hardcoded `specialization: None`, so
  `view v : Engine` dumped as `view v ;`. All now extract the
  feature specialization (shared `_build_full_specialization_from_ud`
  core; `_build_full_specialization_from_ctx` falls back to a direct
  `usageDeclaration` child).
- **`typed_by_name` wiring** — the dispatch branches that assign
  grammar manually (viewpoint, concern, allocation, rendering,
  metadata, individual, constraint, calculation, connection, flow,
  satisfy, dependency, ...) never ran `_extract_specialization_info`; a
  post-pass in `Package.load_from_grammar` now covers them.
  `_extract_specialization_info` is idempotent (re-running would
  append duplicate subsetting names).
- **Registered the `conformance` pytest mark** (no more
  `PytestUnknownMarkWarning`).

*Docs/hygiene:* fixed stale `docs/DEVELOPMENT_PLAN.md` links (→
`docs/archive/`); refreshed AGENTS.md (version, 153-test grammar
status, complete test-file map), STATUS.md Known Issues / Remaining
Work tables, and TODO.md stale Goal-8/palette/next-release bits;
removed tracked debug artifacts (`temp.txt`, `tests/temp.txt`,
`test_puml/*`)

*Known remaining gaps recorded in TODO.md:* nested behavior-usage
typings (`part p { action a1 : A; }`), nested `rendering` public-API
objects, usage-body imports, `satisfy` valuepart.

Fast suite 1484 passed / 2 skipped, conformance 123/123.

## v0.86.0 (2026-09-06)

**Goal 10 close-out — storage backend query parity.**

The last open Goal 10 item ("CayleyStore query extensions — parity
with NetworkX/Kùzu") is closed by making the query surface identical
across all three graph stores:

1. *NetworkXStore* gains `siblings`, `hub_elements` and
   `shortest_path_between_named` (mirroring Kùzu/Cayley semantics,
   deterministic ordering).
2. *KuzuStore* gains `all_paths`, `in_degree_centrality`,
   `out_degree_centrality`, `descendants_depth_limited`,
   `neighborhood` and `impact_analysis` (client-side traversal,
   mirroring the Cayley implementations) plus `hub_elements`
   direction validation and deterministic degree tie-breaking.
3. *Cross-backend parity test* (`TestBackendParity` in
   `tests/store_test.py`): 14 analytics queries run against the same
   element graph on NetworkX, Kùzu and a live Cayley server and must
   return identical results, plus a method-surface assertion.

All store suites verified against a live podman Cayley v0.7 server
(39 cayley tests) and in-memory Kùzu.  Fast suite 1472, conformance
123/123.  **Goal 10 complete.**

## v0.85.0 (2026-09-05)

**Goal 11 Batch 6 — interchange/evaluator.**

1. *Conditional expressions* in the evaluator (`sysmlpy.evaluator`).
   The vendored SysML v2 grammar's conditional spelling is
   ``if <cond> ? <then> else <else>`` (no ``then`` keyword, no
   ``? :`` form).  Ternaries in attribute defaults, constraint bodies,
   and ``calc def`` result expressions now evaluate correctly —
   conditions must be boolean, nested else-chains are supported,
   embedded ternaries inside larger expressions (e.g.
   ``2.0 * (if x > 0 ? 1.5 else 2.5)``) are evaluated via fragment
   substitution, and unit suffixes on branches work
   (``if c ? 3.0 [m] else 2.0 [m]``).  Glued ternary text respaces on
   dump (``if x > 0 ? 1.0 else 2.0``) so models with ternaries
   round-trip through the grammar.
2. *Calc ``in`` parameter invocation*.  Collected ``calc def`` bodies
   are invocable from any expression: positional arguments bind to
   ``in``/``inout`` parameters in order, declared defaults
   (``in h : Real := 2.0``) fill gaps, and recursion is supported up
   to a fixed depth (32).  Constraint bodies can reference calcs with
   what-if ``bindings`` overrides.
3. *Spec-normative JSON-LD context mapping* (`sysmlpy.interchange`).
   :func:`build_jsonld_context` produces explicit property/metaclass
   term definitions mapping every name to ``<vocabulary>#<name>`` —
   the OMG JSON-LD vocabulary convention — so interchange documents
   are self-describing for RDF/JSON-LD tooling.  No OMG-published
   JSON-LD context file exists to bundle (checked against the SysML v2
   pilot implementation), so the vocabulary IRI is configurable via
   :func:`to_interchange` ``vocabulary=`` and
   :data:`INTERCHANGE_VOCABULARY`.  Import side normalizes IRI-keyed
   properties (``<vocab>#<prop>``) back to local names automatically.
4. *CLI export*: ``sysmlpy export FILE --format interchange
   [--vocabulary URI] [--explicit-terms]``.

Tests +38 (`tests/interchange_test.py` extends with vocab/terms/IRI
tests; `tests/evaluator_test.py` adds conditional + calc-param tests).
Fast suite 1469, conformance 123/123.

## v0.84.0 (2026-09-05)

**Goal 11 Batch 5 — performance (cold-start parse).**

1. *Persistent ANTLR DFA cache* (`sysmlpy.dfa_cache`): after the first
   successful parse the warmed parser+lexer ATN/DFA/prediction-context
   graphs are pickled to
   `~/.cache/sysmlpy/dfa-<key>.pkl` (keyed by SHA-1 of both serialized
   ATNs + antlr4 runtime + sysmlpy version + pickle protocol) and
   reinstalled at the start of subsequent processes.  Benchmark
   (`benchmarks/bench_parse.py`, 27 KB model): cold **8–10 s** →
   cached **~2.9 s** — **3.7x faster / ~73-85 % of the cold start
   eliminated**.  Cache failures degrade to normal parsing with a
   one-time warning and never break a parse; `SYSSMLPY_DFA_CACHE=off`
   (or `set_dfa_cache(False)`) disables it; `SYSSMLPY_DFA_CACHE=<dir>`
   overrides the location.
   Pickled-graph identity hazards are repaired on load: unpickled
   `EmptyPredictionContext` copies are rebound to the live
   `PredictionContext.EMPTY` singleton (walk via
   `SingletonPredictionContext.parentCtx` / `ArrayPredictionContext.
   parents`), `EmptySemanticContext` copies to `SemanticContext.NONE`,
   across the shared cache and every DFA config set.  Correctness
   verified by the full grammar suite (143) and OMG conformance suite
   (123) running against a loaded cache.
2. *Visitor profiling* (`benchmarks/profile_parse.py`): the ANTLR
   parse dominates (~80 % of end-to-end, almost entirely
   `adaptivePredict` + token-stream bookkeeping); the visitor and
   grammar classes share the remaining ~20 % across hundreds of small
   helpers with no single hotspot — visitor micro-optimisation
   deliberately not pursued; profiling harness kept under
   `benchmarks/`.

Tests +14 (`tests/dfa_cache_test.py`: round-trip equivalence, corrupt/
wrong-shape/missing cache fallbacks, disable flags, env overrides,
key stability, cross-process save/load).  Fast suite 1469, conformance
123/123.  `set_dfa_cache` exported from the package root.

## v0.83.0 (2026-09-05)

**Goal 11 Batch 4 — LSP enhancements.**

1. *Incremental text sync*: `textDocumentSync.change` is now
   `INCREMENTAL` (2) — ranged `didChange` edits are applied against the
   current text (UTF-16 positions, out-of-range positions clamped);
   range-less changes are still accepted as full-document
   replacements.  `Document.apply_change()` + `_pos_to_index()`.
2. *Position-tracked semantic diagnostics*: the symbol walk visits
   model elements in declaration order, so the *n*-th element with a
   given `(kind, name)` pairs with the *n*-th declaration occurrence
   of that pair in the text — duplicate names get their own
   declaration's range, and definitions prefer their `def` occurrence.
   Semantic issues now take their range from the owning element's
   paired location (with the quoted-name heuristic and
   `SemanticIssue.reference` as fallbacks); `reparse` builds the
   symbol index before analyzing.
3. *workspace/symbol*: case-insensitive substring query across all
   open documents plus `*.sysml` files under the initialized
   `rootUri`/`workspaceFolders` root (capped at 100 files, results at
   200; cached until the next document change; unparsable files
   skipped; open documents are not duplicated by the root scan).
4. *`.`-member completion*: completion right after ``base.`` returns
   the direct members of the resolved type of *base* — a typed part's
   definition, or a definition named directly — filtered by the typed
   prefix.  Resolution falls back to the **last successfully parsed
   model** when the document is transiently unparsable (half-typed
   expression), and the keyword/name fallback list is built from that
   model too; outline/hover/definition still degrade to empty.

LSP tests 37 → 73 (`tests/lsp_test.py` + new `tests/lsp_batch4_test.py`).
Fast suite 1455, conformance 123/123.  docs/LSP.md and
docs/LSP_EDITORS.md updated.

## v0.82.0 (2026-09-05)

**Goal 11 Batch 3 — diff batch 2.**

1. *Rename detection*: removed+added pairs with equal kind and equal
   structural signature (typing/subject/value/multiplicity/direction/
   abstract/traces — `doc` excluded, it often changes with the name)
   match as `renamed` when the candidate is unique; ambiguous
   signatures stay removed+added.  `ElementChange.old_name` /
   `old_qualified_name` carry the previous identity; summary, text
   (`>` marker) and markdown render renames.
2. *Grammar-level signature fields*: `value` (default-value
   expression), `multiplicity` (`[2]`, `[1..3] ordered nonunique`),
   `direction` (in/out/inout) and `abstract` are heuristic reads of
   the element's canonical `dump()` text.  Documentation is a tree
   attribute (requirements) — `doc /* ... */` does not survive the
   grammar round-trip on usage/definition kinds.
3. *Requirement trace edges*: signature field `traces` (sorted
   `satisfy:x`, `verify:y` edges via
   `traceability.extract_traceability`) — satisfy/verify changes now
   surface as field changes.
4. *State-machine diff*: `diff_state_machines(old, new, focus=None)`
   diffs two models' machines via the simulator's
   `MachineDescriptor` — initial state, states, transitions
   (source/target/trigger/guard/effect/history_region), named or
   endpoint-identified anonymous transitions.
5. *`--threshold` CI gate*: `sysmlpy diff OLD NEW --threshold 0.1`
   exits 1 only when the change rate (changes / old elements,
   `ModelDiff.change_rate`) exceeds the fraction;
   `elements_old`/`elements_new`/`change_rate` in the JSON output.

Also fixed: `requirement r2 :>> r1;` (and interface/message loads with
redefinitions) crashed with `AttributeError: '_redefined_refs'` —
`Requirement.__init__` / `Interface.__init__` / `Message.__init__` now
initialize base-`Usage` state (same family as the v0.79.1 `Reference`
fix).

Diff tests 14 → 41 (`tests/diff_test.py`).  Fast suite 1419,
conformance 123/123.

## v0.81.0 (2026-09-05)

**Goal 11 Batch 2 — sim: assignment effects + history pseudostates.**

1. *Assignment effects execute*: `do x := 5` (general
   `do <name> := <expr>`) is evaluated via `evaluate_expression` and
   applied through `StateSimulator.set_value`, so guards evaluated
   later see the new value.  Applied pairs surface on
   `StepRecord.assignments` (and the log repr).  Failed evaluations
   (unknown name, type errors) never abort the simulation — the
   effect is logged with a `(not evaluated: ...)` annotation.
2. *History pseudostates*: `state h : HistoryUsage;` /
   `h : HistoryUsage;` (typed) and bare `h;`/`history;` (name
   convention, untyped references only) are recognized as history
   markers — `boxes_view._collect_state_machine` reports them in a
   new per-region `pseudostates` list, they are excluded from the
   state list, and transitions targeting them re-enter the region's
   last active substate (falling back to the region's default entry
   when nothing was recorded yet).  Deep history (restore the deepest
   visited state) via `StateSimulator(..., deep_history=True)` and
   `sysmlpy sim --deep-history` — the language has no deep-history
   form, so it is a simulator option.

Sim tests 38 → 52 (`tests/sim_test.py`).  Fast suite 1394,
conformance 123/123.

## v0.80.0 (2026-09-05)

**Constraint textual bodies** — natural-language constraint capture.

1. *Tagged bodies*: `rep language "English" /* ... */` inside a
   constraint (or calculation) body is now kept by the visitor (it was
   silently dropped in body context) and exposed on the public API via
   `Constraint.body_text` / `Constraint.body_language` /
   `textual_representations()`.  `check_constraints()` reports such
   constraints as "not machine-evaluable — textual body in language
   'English': '...'" instead of skipping them.  Dump round-trips
   byte-stably (canonical form drops the optional `rep` keyword —
   grammatically identical, same precedent as `nonunique ordered`).
2. *Rescue pass* (`sysmlpy.antlr_parser`): when a parse fails, every
   `constraint ... { ... }` body is trial-parsed and failing bodies are
   salvaged as textual representations (default language `"English"`,
   configurable via the new `rescue_language` parameter threaded
   through `loads()` / `load_grammar()` / `parse()`), then the model is
   re-parsed.  One natural-language constraint no longer fails the
   whole model load; a `UserWarning` names every salvaged constraint.
   Bodies containing `*/` cannot be wrapped and keep the original
   error; valid constraint bodies are never touched.

Also fixed: parsed `constraint` / `calculation` / `state` /
`requirement` / `allocation` usages appeared in the object tree as
anonymous (`name is None`) — ConstraintUsage's declaration chain nests
one level deeper than the old name extraction walked.

12 new tests (`tests/constraint_text_test.py`).  Fast suite 1380,
conformance 123/123.

## v0.79.1 (2026-09-05)

**`ref` usages now appear in the object tree** — they were silently
dropped at two levels:

- *Package-level* `ref r : Engine;` — the visitor's package-member
  dispatch (`_visit_usage_element_dict`) had no `referenceUsage`
  branch, so the member never reached the grammar dict (the nested
  body path already had one).  Package-level refs round-trip through
  `dump()` before this fix only because the raw grammar text was
  re-serialized; the object tree never saw them.
- *Nested* `ref driver : Person;` inside part bodies — the grammar
  kept them, but the public-API class dispatch (base
  `Usage.load_from_grammar` and `Package.load_from_grammar`) had no
  `ReferenceUsage` branch.

New `Reference.load_from_grammar` extracts name / typing /
redefinition from the grammar node (the bare redefinition form
`ref :>> payload : Fuel;` has null `declaredName` — the name comes
from the Redefinitions chain) and `usage_dump` re-serializes from the
grammar so round-trips stay byte-identical.  `resolve_types()` now
also links parsed refs (`ref_type`/`typedby`).

Also fixed: `Reference.__init__` did not initialize the base-Usage
state, so freshly built objects crashed `repr()` / `is_definition`
with `AttributeError` on `_is_definition`.

12 new tests (`tests/reference_parse_test.py`).  Fast suite 1368,
conformance 123/123.

## v0.79.0 (2026-09-05)

**Goal 11 batch 1 — model semantics (typedby resolution + Cayley
query extensions).**

- **`Model.resolve_types()`** — model-wide pass linking each usage's
  declared type name (`typed_by_name`, preserved since v0.57.0) to
  its definition *object* (`typedby`), closing the long-tracked gap
  where the object link only existed for programmatic wiring.
  Resolves simple names, `::`-qualified paths and relative qualified
  paths (`Types::Wheel` declared inside `Vehicle`); library typings
  and unresolved names are left untouched; ambiguous simple names
  resolve to the usage's own package first.  Idempotent; returns the
  resolve count.
- **Serialization-safe typedby** — `Usage._get_definition` no longer
  inserts the typed-by definition when it is already part of the
  model tree (`_typedby_serialized_elsewhere`): parsed models whose
  `typedby` was filled in by `resolve_types()` (and programmatic
  models whose definition is an explicit package member) dump
  byte-identically, while standalone programmatic wiring still
  hoists the definition into the package output.  `Model.load` now
  sets `parent` on loaded packages so the guard can see the whole
  tree.
- **CayleyStore query extensions** — `all_paths`,
  `in_degree_centrality`, `out_degree_centrality`,
  `descendants_depth_limited`, `neighborhood`, `impact_analysis`,
  `siblings`, `hub_elements`, `shortest_path_between_named` —
  closing the API gap with NetworkX/Kuzu (client-side over the
  gizmo primitives; shapes match the NetworkX/Kuzu tests).  17 new
  live-server tests incl. a centrality parity check.
- 29 new tests (12 `tests/resolve_test.py`, 17 Cayley live).  Fast
  suite 1356, conformance 123/123.

## v0.78.0 (2026-09-05)

- **Documentation consolidation** — README refreshed: new
  *Command-Line Tools* section (all 12 subcommands + `sysmlpy-lsp`,
  CI exit codes, examples), stale claims removed (the "dimension
  derivation not yet implemented" note — shipped in v0.75.0 — and a
  mismatched legacy example), Cayley instructions updated with the
  tested podman command, OCL table points to the full 31-code
  catalogue.  `docs/index.md` rewritten (new highlights + links incl.
  sim/LSP/GUARDS/archive).  TUTORIAL refreshed with semantic
  analysis, model diff, CLI, and storage-backend sections, plus a
  "Where to Go Next" table.  PROJECT_SUMMARY refreshed (v0.60.0 →
  v0.78.0 state).  New `docs/archive/` holds retired documents
  (PySysML2 comparison, completed development plan, reference
  analyses) with a provenance README.
- **Every documented snippet now validated against the code** — the
  audit found the docs had drifted (or never worked):
  - `classtree(loads(text))` — the README/TUTORIAL-documented form —
    **always raised TypeError** (it only accepted grammar dicts;
    `tests/class_test.py` had silently shadowed `loads` with
    `load_grammar`).  The Model form is now supported and returns
    the model's RootNamespace.
  - `load_partial(text)` success path returned a `RootNamespace`
    grammar object, violating its own docstring ("typed Model") —
    now returns a real `Model` via `Model._load_definition`.
  - `Reference.dump()` dropped the `: Type` suffix whenever the
    typed-by element had no children (falsy via
    `Searchable.__len__`) — `set_type(Item(...))` rendered as bare
    `ref driver;`.  Now `ref driver : Person;` as documented.
  - Grammar reality documented: bare `import X;` is invalid (a
    visibility keyword is required); dump formats corrected
    (`mass= 100[kilogram]`, `thrust= 1199[newton]`); `count()` is
    package-level/non-recursive; `AnalysisResult` has no `summary()`.
- 3 new tests (classtree Model form, Reference typed dump,
  load_partial Model contract).  Fast suite 1327, conformance
  123/123.

## v0.77.0 (2026-09-05)

- **Goal 10 batch 3: CayleyStore hardening + query parity (Goal 10
  complete)** — verified against a live Cayley v0.7 server
  (`podman run -d --name cayley -p 64210:64210
  docker.io/cayleygraph/cayley`).  Fixes, all found by probing the
  real server:
  - `clear()` called a nonexistent `_query_label` (AttributeError);
    now label-scoped via the `_store_label` marker
  - `_delete_quads()` posted to `/api/v1/write` (which *adds* quads —
    a silent no-op for existing ones) instead of `/api/v1/delete`;
    nothing was ever actually deleted
  - `delete()` built its quad list but never sent it; now performs
    true deletion including incoming relationship edges (no ghost
    links in `parents()`/`children()`)
  - `get()` leaked `_is_element`/`_store_label` markers and folded
    relationship edges into the data dict; now returns exactly the
    `put()` data (parity with InMemory/NetworkX)
  - `put()` overwrite semantics: replaces property quads, keeps
    relationship edges (was non-deterministic on re-put)
  - `__len__` counted the whole database (`g.V().count()`) instead
    of this store's elements
  - `query()` glob parity: `name="p*"` etc. now use the client-side
    `fnmatch` path (Cayley `has()` matches literally); verified
    identical results to NetworkXStore across 9 filter shapes
  - `query()` with no filters returned raw dicts instead of IDs
  - `subgraph()` created bogus self-edges and wiped properties with
    a second empty `put()`
- **Label namespacing**: Cayley gizmo queries are quad-label-blind —
  two stores sharing a server with the same subject IDs see each
  other's quads.  Stored subjects now carry the store label
  (`<label>:<element_id>`); the public API keeps unprefixed IDs.
  Discovered when the previously-unrunnable
  `tests/cayley_store_test.py` (22 tests, requires a live server)
  collided with the new `TestCayleyStore` class.
- `requests` added as the optional `cayley` extra
  (`poetry install --extras cayley`).
- 21 new tests (`tests/store_test.py::TestCayleyStore`, skipped when
  no server at localhost:64210).

## v0.76.0 (2026-09-05)

- **Goal 10 batch 2: connector-end type compatibility** —
  `CONNECTOR_END_TYPE_MISMATCH` (warning, rule code 31): when both
  ends of a connection resolve to typings that are *local* `port
  def` names and neither is a (transitive) specialization of the
  other, the connection is flagged — conjugation only makes ports of
  the same (or related) port definition compatible.  Chained ends
  (`e.drive to w.hub`) resolve typing through member maps; ends
  typed by library/external port definitions and part-to-part ends
  are skipped (no local subclass data; direct part connections are
  idiomatic SysML).  Implemented in the Goal 9 batch 6 connector
  walk, which already resolves end chains — the old
  `_check_connector_end` stub (`pass`) is superseded.
- **Goal 10 batch 2: regex -> parser import extraction** —
  `_extract_imports` (dependency scanning for `load_files` /
  `load_project`) now scans the SysML v2 lexer token stream instead
  of a raw-text regex, fixing three defects: bare `import X::Y;`
  (no visibility keyword) was missed entirely; imports inside
  comments produced false positives; imports inside string literals
  (`doc about "..."`) produced false positives.  Scanning tolerates
  syntax errors (dependency scanning must not require a parseable
  file).  The remaining regex use in project.py
  (`_defines_package`) is a simple file-header check, kept.
- 11 new tests (7 connector in `tests/validator_test.py`, 4
  extraction in `tests/project_test.py`).

## v0.75.0 (2026-09-05)

- **Goal 10 batch 1: `*`/`/` unit-dimension derivation** — the
  analyzer now derives the dimension of an initializer algebraically
  and compares it with the declared quantity type:
  - `attribute f : ForceValue = mass * speed;` errors
    (`UNIT_DIMENSION_DERIVATION_MISMATCH`, rule code 30): mass*speed
    derives `L^1*M^1*T^-1` but ForceValue is `L^1*M^1*T^-2`.
  - Algebra: `*` adds exponents, `/` subtracts, `**`/`^` with a
    literal-integer exponent multiplies; dimensionless literals are
    the multiplicative identity. `+`/`-` chains must keep equal
    operand dimensions (unequal ones stay with the existing pair
    check, so no double reporting).
  - Conservative skips (no false positives): unknown-dimension
    operands, non-literal exponents, `%`, boolean/string/relational
    levels, constraint bodies (owners without quantity typing), and
    initializers with no quantity-typed operand at all (a bare
    `= 70` cannot reveal its intended unit).
  - Wired as Step 4c: `SemanticAnalyzer._check_expression_derivations`
    -> `ExpressionTypeChecker.check_derivations`; visitor expression
    shapes mirror `const_fold`'s layer walk (operator-less wrapper
    levels, parallel operator/operand list form for exponentiation).
- **SLL error parity** — `parse(prediction_mode="sll_only")` now
  keeps the fallback pass in SLL prediction too: its diagnostics
  match the fast-path behaviour (previously stage 2 silently ran
  LL). Forced `ll` mode is unchanged.
- 14 new tests (9 derivation in `tests/semantic_test.py`, 5 SLL in
  `tests/two_stage_parse_test.py`).

## v0.74.0 (2026-09-05)

- **Goal 8 batch 1: semantic model diff** (`sysmlpy.diff`) —
  - `diff_models(old, new)` / `diff_files(a, b)` compare two models
    element-by-element; identity is `(kind, qualified name)` with a
    `Def`/`Usage` kind suffix, so repurposing a name across roles
    reports as removed + added, not a silent change.
  - Element signatures compare typing (`typed_by_name`, qualified),
    requirement subjects and doc text; changes report field-level
    old/new values.
  - `ModelDiff` renders as monochrome text, Markdown (review
    workflows) and JSON; renames surface as removed + added pairs
    (heuristic rename detection is a tracked follow-up).
  - CLI: `sysmlpy diff old.sysml new.sysml [--format
    text|markdown|json]` — exit 0 identical, 1 differences, 2 load
    failure (CI gate for review).
  - Excluded by design: Model objects (random UUID per parse),
    transitions (grammar-dict riders, not tree objects — sim
    descriptor diff is a follow-up), values/multiplicities/directions
    (grammar dicts — follow-up batch).
- Lazy exports `diff_models` / `diff_files` / `ModelDiff` /
  `ElementChange` / `FieldChange` from `sysmlpy.__getattr__`.
- 16 new tests (`tests/diff_test.py`).

## v0.73.0 (2026-09-05)

- **Goal 9 batch 6: connector ends + subject types** —
  - `UNRESOLVED_CONNECTOR_END` (error): a connection-end chain whose
    segment provably does not resolve in a known, non-specializing
    container is flagged.  Conservative skips: containers typed by
    library/external defs, unknown (non-model) types, and subclasses
    (inherited members could supply the missing feature).
  - **Chains through port typings** (`connect a.p1.bus.pb to b.p2`):
    port usages now contribute their typing to the resolution maps,
    so feature chains crossing port-owned structure resolve.
  - `SATISFY_SUBJECT_TYPE_MISMATCH` (warning): `satisfy <req> by
    <part>` where the by-part's type is unrelated (no specialization
    path either way) to the requirement's typed subject.  Skips
    untyped parts, absent subjects and library types.
  - **Abstract-typing warnings dropped by design** — typing a part by
    an abstract definition is valid SysML v2 (instances come from
    concrete specializations); flagging it would generate false
    positives.  The spec research question is settled as "no check".
- 10 new validator tests (77).

## v0.72.0 (2026-09-04)

- **Goal 9 batch 5: satisfy parts + nested coverage + deep chains** —
  - **Bug fix: satisfies nested inside requirement bodies** now count
    as coverage.  `requirement top { satisfy top by v; }` parsed fine
    but was invisible to `extract_traceability()` (the visitor
    handles nested *verify* members, not satisfy), so the requirement
    read as REQUIREMENT_UNCOVERED and the trace edge was missing.
    Nested satisfy members are now extracted from the requirement's
    grammar dict and recorded on the trace.
  - `UNRESOLVED_SATISFY_PART` (error): the `by <part>` reference of a
    satisfy member resolves against the symbol table — both
    package-level and nested members.
  - **Deep feature-chain connection ends** (`connect bus.a.p3 to
    b.p2`) now resolve for direction checks: segment 0 through the
    part's typing, middle segments through member typing in the
    resolved container, final port through the container's port
    directions.  Batch 4 handled chains up to two segments.
  - The stale `[Requirement] Unhandled nested requirement type`
    print no longer fires for satisfy/verify members (both handled).
- Defer: `satisfy` subject *type* compatibility (needs an
  inheritance walk — subject type vs by-part type subtyping).
- 6 new validator tests (67).

## v0.71.0 (2026-09-04)

- **Goal 9 batch 4: verify targets + connector directions** —
  - `UNRESOLVED_VERIFY_TARGET` (error): `verify <vc>` members inside
    requirements resolve against the symbol table.  The visitor drops
    the `: VC` typing specialization on verify members entirely
    (`fsp` is empty), so a typo'd verification-case *type* is
    invisible in the parse tree — but the member's reference name is
    checkable, and now is.
  - `CONNECTOR_DIRECTION_MISMATCH` (warning): `connection c connect
    a.p1 to b.p2` with both ends carrying explicit non-`inout`
    directions in the same direction (`out`→`out`, `in`→`in`).
    Resolves both end chains — two-segment chains through part
    typings (`a.p1` via a's typed-by def) and single-segment chains
    against the enclosing scope.  Undirected, `inout` and
    deeper-chain ends are skipped (advisory, not an error —
    conjugated ports and exotic flow conventions exist).
- 8 new validator tests (61).

## v0.70.0 (2026-09-04)

- **Goal 9 batch 3: trace-target checks** —
  - `UNRESOLVED_TRACE_TARGET` (error): a `satisfy <req> by <part>`
    target that names no declared requirement.  A typo'd target was
    doubly silent before: the trace edge died quietly AND the Goal 2
    coverage extractor materialized the dangling edge as a *phantom
    requirement* — the real requirement read uncovered while a fake
    one appeared traced.
  - `TRACE_TARGET_NOT_REQUIREMENT` (warning): a target that resolves
    but to a non-`Requirement` element.  Library-resolved targets are
    left alone (conservative — no model element to inspect).
- **Scoping note**: abstract-typing warnings were dropped from this
  batch after probing — typing by an abstract definition inside an
  abstract definition is legitimate modeling (redefinition is the
  intended mechanism), so the rule needs spec research before it can
  be implemented without false positives.
- 4 new validator tests (53).

## v0.69.1 (2026-09-04)

- **Goal 9 batch 2: trigger-payload and requirement-coverage checks** —
  - `UNRESOLVED_TRIGGER_PAYLOAD` (error): `accept <Sig>` payload names
    (both bare and `when`-guarded forms) resolve against the symbol
    table in the transition's scope; a typo'd payload previously
    slipped through silently — the transition just never fired.  When
    both an identification and a typing exist (`accept e : T`), only
    the typing is a reference (the identification is a fresh
    declaration).
  - `REQUIREMENT_UNCOVERED` (warning): requirement *usages* with no
    `satisfy` and no `verify` relationship, via the Goal 2
    traceability extractor.  `requirement def` categories are never
    flagged; partial coverage (satisfied xor verified) is not flagged.
- **Fixed**: `analyze()` crashed with `UnboundLocalError` on models
  parsed without the optional `sim` extra — the state-machine
  well-formedness checks now skip cleanly instead.
- 8 new validator tests (49 total in validator_test.py).

## v0.69.0 (2026-09-02)

- **Goal 9 begins: state-machine well-formedness checks** — three new
  OCL rules in `analyze()`: `UNRESOLVED_TRANSITION_ENDPOINT` (error —
  a transition endpoint that names no state in its machine),
  `NO_INITIAL_STATE` (warning — >1 state and no `entry; then X;`), and
  `UNREACHABLE_STATE` (warning — no path from the initial state).  All
  three run on the simulator's expanded descriptor, so composite
  regions, bare-name substate references and composite entry
  retargeting are resolved the same way simulation resolves them.
  Supporting change: `MachineDescriptor.skipped` now carries
  transitions excluded from simulation as structured data (previously
  note-text only), and machine-wide bare-name resolution replaced the
  sim's implicit state addition — unknown endpoints are skipped
  (diagnostics see them) instead of silently becoming states.
- **State-machine simulation (MVP, `sysmlpy sim`)** — Cameo-style
  simulate-and-step for `state def` machines: `StateSimulator` builds an
  executable machine from a parsed model and drives it — `send(trigger)`
  fires transitions, guards evaluate **for real** against the model's
  attribute values (pint-aware, via the v0.64 evaluator) plus
  `set_value`/`--set` what-if overrides, effects log as text, completion
  transitions (no `accept` trigger) fire run-to-completion, and
  `--run "T1; T2"` scripts a session for demos/CI.  Execution delegates
  to the optional `transitions` library (new `sim` extra) — chosen over
  python-statemachine because it builds machines from *data* at runtime,
  the exact shape of the SysML→machine bridge.  Reuses the boxes-view
  machine collector for states/initial/composites.
  - **Boxes-view transition extraction fix** — `_extract_transition_elements`
    reported `trigger: 'key'` for `accept Engage when key` (the guard's
    own feature name — the generic QualifiedName search tripped over the
    guard) and dropped shorthand guards/effects entirely.  It now takes
    the trigger from the payload's `declaredName`, the guard from the
    `TriggerExpression` (`kind.isWhen`), and adds an `effect` slot; the
    TargetTransitionUsage shorthand gets the same treatment.  Guards now
    appear in stv/boxes edge labels.
  - **Transition `do` effects now parse** — the visitor emitted
    `EffectBehaviorMember.ownedRelatedElement = null` (the effect
    reference was dropped at the visitor level).  It now visits the
    grammar's real `effectBehaviorUsage` shape, emitting the
    class-constructable `EffectBehaviorUsage`/`PerformedActionUsage`
    dicts for `do <behavior-reference>` (round-trips through
    `dump()`), and carries the send/accept/assignment declarations as
    a readable sibling `text` (e.g. `send Alert to logger`);
    assignment effects render `target := value` (e.g. `x := 5`) in the
    simulator.  The simulator's effect logging lights up untouched.
  - **Colorblind-safe palette option** — `set_stereotype_palette("okabe-ito")`
    switches every `style="color"` view to the Okabe-Ito palette (the
    historical default pairs lime-green parts against red requirements —
    indistinguishable under protanopia/deuteranopia).  `bw` stays the
    default style and renders no colors regardless.
  - **Composite-state regions simulate** — regions expand flat with
    qualified names (`Composite.Sub`, nesting supported): transitions
    targeting a composite enter its initial substate (UML default
    entry), the region runs its own transitions, and transitions
    declared on the composite apply from every substate (UML
    composite transitions — deeper transitions win the fall-through).
    Parallel regions (top-level or inside a composite) raise.
  - 38 new tests (`tests/sim_test.py`); plantuml 151, boxes 54, core
    suites 707, conformance 123.

- **Docs** — AGENTS.md pitfall 7: bare `import` without a visibility
  keyword is non-conformant per the OMG standard (visibility is
  required; confirmed against the textual standard and XPect source);
  the grammar's rejection of it is correct, not a gap.

- **Action Flow View control nodes** — `as_action_flow_view()` now renders
  SysML v2 control nodes from action bodies: `first start` as a solid
  initial dot, `decide`/`merge`/`fork`/`join` as hexagon nodes with
  stereotypes, and `done`/`terminate` succession targets as a final
  circle. Chain edges are dotted successions (`..>`, per the pilot's
  `VAction`) with guard conditions (`if <cond> then X`) and `else`
  as labels. Grammar-only `ControlNode` children no longer leak as
  anonymous containment boxes. 11 new tests
  (`TestActionFlowControlNodes`).
- **Interconnection View notation fidelity** — `as_interconnection_view()`
  now follows the official iv notation: part nesting is conveyed by
  **enclosure** (nested `rectangle` blocks) instead of `*--` composition
  edges; usages carry **typed labels** (`s : Sensor`) instead of
  `--:|>` typing arrows; definitions typed by rendered usages are not
  drawn (their ports inherit onto the usages as boundary boxes);
  flows and connections render **only as edges** — flows port-to-port
  with declared names recovered from the grammar (`flow f1 from
  s.output to p.input` labels `f1`, previously collapsed to
  part-to-part "flow"), `connection ... connect x.p1 to y.p2` usages
  render as thick plain lines (`_extract_connections` was already
  present but never wired into the iv). Anonymous flow UUID names are
  suppressed as before. 5 new tests.
- **Package View namespace enclosure** — `as_package_view()` now follows
  the official package notation (pilot `VStructure.casePackage`):
  packages render as `package "Name" { members }` blocks with their
  owned members **nested inside**; definitions render as leaf boxes
  without exploding their features (features belong to the
  definition's namespace, not the package); containment is conveyed
  entirely by enclosure — no `*--` edges, fixing the old behavior
  where only sub-packages nested and every feature floated
  free-standing. Members carry typed labels (`myCar : Vehicle`);
  typing/specialization arrows between rendered members are kept
  unlabeled (the pilot draws them unlabeled); `focus` and
  `max_depth` work on the namespace tree. Orphaned `_render_package`
  removed. 4 new tests (plantuml 151). Example 08 regenerated.
- **Flow endpoint chains** — `_extract_flow_endpoints` now recovers the
  full feature path (`s.output`, not just `s`): FlowFeatureMember →
  FlowFeature → FlowRedefinition carries the chained segment as its
  child QualifiedName; anonymous flows fall back to their declared
  name via `Identification.declaredName` (`_flow_declared_name`).
  Afv behavior verified unchanged (flows still connect actions, per
  the pilot's VAction).
- **Boxes-backed afv control nodes** — `as_action_flow_view_boxes()`
  renders the same chains through diagramboxes primitives: `first
  start` as a filled start dot, `decide`/`merge` as **diamonds**
  (`DecisionNode`, parented inside the composite action), done /
  terminate targets as done bullseyes, fork/join as bars; chain edges
  are dashed successions with guard labels. Requires diagramboxes
  0.5.0 (`parent=` support on the diamond/bar factories). +6 tests
  (`TestActionFlowControlBoxes`, 54 total in boxes_view_test).
- **diagramboxes 0.5.0 port routing** — the sugiyama engine's port
  routing is obstacle-aware: side-facing port edges wrap around node
  bodies through free bands instead of slicing through boxes placed
  between the endpoints; single-ported edges anchor at the port
  boundary. Benefits the boxes iv/stv/afv under `routing='sugiyama'`.

## v0.68.0 (2026-09-03)

### :white_check_mark: Boxes-backed views (iv + afv) & legend defaults


- Sibling package `boxes` renamed to `diagramboxes` (its v0.3.0) —
  PyPI name collision. `sysmlpy.boxes_view` imports the new name and
  the ImportError hint is updated; the 19 boxes-adapter tests now run
  (they were skipping against a stale install).
- **Nested composite states in the boxes view** (diagramboxes v0.4.0
  layout pass): `as_state_transition_view_boxes` now renders composite
  states as real containment (sub-states drawn inside the parent box,
  parented initial/final pseudostates, internal transitions routed
  inside the composite) instead of flattening `Parent.Sub` labels.
  Transition resolution gained a last-segment fallback so
  `transition Running then Stopped;` (target nested in Running)
  resolves from the enclosing level. 24 adapter tests.
- **Boxes-backed action flow view** —
  `as_action_flow_view_boxes()` renders action usages as boxes
  («action» + type), declared action parameters as boundary ports
  (in/left, out/right — `label_inside` placement), and flow
  connections as port-to-port edges
  (`flow providePower.torque to injectFuel.fuelCommand`). Inline
  nested actions render as composite children; action defs containing
  structure render as «action def» boxes with their nested actions
  inside; structure-less defs surface only through their typed
  usages' ports. `focus=` keeps the subtree plus flow partners.
  Successions between nested actions
  (`succession s1 first torque then inject;`) render as dashed
  edges (..> per the official notation). Container-to-own-child
  flows (def parameter feeding a nested action) are skipped — they
  would re-anchor to self edges in the nested layout. 16 more tests
  (48 total adapter tests).
- **Boxes-backed interconnection view** —
  `as_interconnection_view_boxes()` renders part usages as boxes with
  boundary ports and `connection` usages as port-to-port edges
  (Z-routed); endpoints chained through ports
  (`connect engine.powerOut to drivetrain.powerIn`) create the ports;
  `focus=` filters by part; braille + SVG render helpers. Ports use
  the new diagramboxes `label_inside` placement so labels stay clear
  of the box text. 8 more tests (32 total).
- **Relationship legends are now opt-in** (`include_legend=False` by
  default across `to_plantuml`, `PlantUMLGenerator`, and all view
  functions). The built-in legends listed relationship notations
  (typing `--:|>`, composite `*--`, binding thickness, …) that are
  already defined by the standard — redundant noise for readers.
  Pass `include_legend=True` to request one. The boxes stv legend
  (which explains our own ASCII rendering conventions, not standard
  notation) remains available and off by default.
- **Accessibility note**: the monochrome `"bw"` style remains the
  default everywhere; `"color"` styling stays opt-in via `style=`.
  A dedicated color-vision-safe palette option is tracked for a
  later release (see TODO.md).

## v0.67.0 (2026-09-03)

### :white_check_mark: PlantUML notation fidelity — official SysML v2 graphical conventions (Adoption Roadmap Goal 6, phase 1)

Ground truth: the OMG pilot implementation's PlantUML generator
(`SysML2PlantUMLStyle`) and the "Intro to the SysML v2 Language —
Graphical Notation" figures (Release 2026-04). A research corpus is
kept at `~/research/notation_corpus/` (123 rasterized official
notation pages + 646 named spec figures + an edge-encoding analysis;
the SysML v2 Book is a secondary source with known non-standard
figures).

- **Edge encodings aligned to the official reference**
  (`ARROW_STYLES`): connections are thick *plain* lines
  (`-[thickness=3]-`, arrowhead only when metadata is present);
  bindings/feature values are the heaviest line (`-[thickness=5]-`,
  «bind»/`=`); allocation is `thickness=5,dotted`; typing keeps its
  own arrow (`--:|>`); redefinition is visually distinct from
  specialization (`--||>` vs `--|>`).
- **New edge types**: send action `..>>`, accept action `<<..`
  (reversed), variant membership `+---`, objective membership `-->>`,
  metadata annotation `..@`, succession flow `..>`, perform/exhibit/
  include-use-case `-->`; `derive` corrected from a misleading
  `*--` to the labeled dashed form (spec figure).
- **Connection endpoints now parse** — the visitor's `ConnectionUsage`
  stub (`"part": None`) is fixed: `connect X to Y` is captured via
  ConnectorPart → BinaryConnectorPart → ConnectorEndMember →
  ConnectorEnd → OwnedReferenceSubsetting (reuses the existing
  `_visit_connector_end_member`/`_visit_connector_end` visitors used
  by transition successions). Round-trip intact (143 grammar tests).
- **General View (gv) renders connector edges** — new
  `auto_include_connections=True` flag emits `E1 -[thickness=3]- E2 :
  clutch` edges (opt-in, backwards compatible).
- **State Transition View (stv) renders composite states as nested
  PlantUML state blocks** (official containment notation) instead of
  flattening them and drawing containment as fake transition arrows.
  Initial/final markers, transition labels, and legends updated.
- **Legends updated** in gv/iv/afv/stv to the official encodings.

New `tests/plantuml_test.py::TestOfficialNotationV067` — 9 tests
(arrow table, endpoint extraction, gv connection edges, legends,
nested states, no fake containment transitions, initial/final
markers). Fast suite now 1082 passed + 25 skipped + 123 conformance =
1205 total, all passing.

## v0.66.0 (2026-09-03)

### :white_check_mark: Spreadsheet bridge — CSV/XLSX export, value import (Adoption Roadmap Goal 7)

Also: **`docs/LSP_EDITORS.md`** — a practical setup guide for using the
LSP server in Neovim (0.11+ `vim.lsp.config` and 0.8–0.10
nvim-lspconfig) and VS Code (dev host + .vsix packaging, settings
reference), registered in the MkDocs nav.

- **New `sysmlpy.spreadsheet` module** (exported from the package
  root):
  - CSV export of the three tabular views: new `output_format="csv"`
    on `as_tabular_view` / `as_data_value_tabular_view` /
    `as_relationship_matrix_view` (shared `_format_table_rows_csv`
    helper, proper quoting via the `csv` module), plus thin wrappers
    `tabular_view_to_csv()` / `data_value_tabular_to_csv()` /
    `relationship_matrix_to_csv()`.
  - `write_xlsx(model, path, include=…)` — Excel workbook with one
    bold-headed sheet per view (Tabular / DataValues / Matrix);
    requires the new optional **`xlsx` extra** (`pip install
    'sysmlpy[xlsx]'` → openpyxl ≥ 3.1); a missing openpyxl raises a
    clear `ImportError` instead of failing mid-export.
  - **Value import**: `import_values_csv()` / `import_values_xlsx()`
    parse spreadsheet rows into evaluator **bindings** — headers
    `Name,Value[,Unit]` or `Element,Attribute,Value[,Unit]`; values
    parse via `parse_value_literal()` (bool → int → float → pint
    quantity → string). Compose with the Goal 4 evaluator:
    `check_constraints(model, bindings=import_values_csv("v.csv"))` —
    spreadsheet-driven constraint gates.
- **CLI**:
  - `sysmlpy view FILE --view tabular --format csv` (and data-value /
    matrix views) — new `csv` output format.
  - `sysmlpy eval FILE --constraints --set-file values.csv` — load
    what-if values from CSV/XLSX (BOM-tolerant; `--set` flags win over
    file values; exit 1 on constraint failures).
  - New **`sysmlpy xlsx FILE -o model.xlsx [--sheets …] [--focus …]`**
    subcommand for the workbook export.

New `tests/spreadsheet_test.py` — 37 tests (CSV quoting, header/row
shape, focus behavior, XLSX sheets/selection/bold headers, import
layouts incl. units, CLI integration; openpyxl-dependent tests skip
gracefully). Fast suite: 1070 passed + 25 skipped (optional-dep guards) + 123 conformance = 1193 total.

## v0.65.0 (2026-09-03)

### :white_check_mark: LSP server — editor integration (Adoption Roadmap Goal 5)

sysmlpy now speaks the Language Server Protocol: live diagnostics and
model navigation in any LSP editor (VS Code, Neovim, Emacs, …).

- **New `sysmlpy.lsp` package** (dependency-free — hand-rolled LSP 3.17
  subset over JSON-RPC `Content-Length` stdio framing):
  - `protocol.py` — byte-stream framing (encode/read, tolerant header
    parsing), LSP error codes and symbol kinds.
  - `server.py` — transport-agnostic `SysmlLanguageServer` (message
    dict in → message dicts out) and `DocumentIndex` (one cached
    parse+analyze snapshot per document version feeding all features).
  - `stdio.py` — stdio transport loop; `sysmlpy-lsp` console script
    (new in pyproject) and `python -m sysmlpy.lsp`; `--log FILE` for
    protocol traces, `--version`.
- **Features**:
  - `publishDiagnostics` — ANTLR syntax errors with exact line:column
    ranges; semantic issues from `analyze()` located in the text via a
    quoted-name heuristic (position-tracked parser tracked as
    follow-up; syntax positions are exact).
  - `documentSymbol` — hierarchical outline with LSP SymbolKind mapping
    (package→Package, defs→Class, attributes→Field, …) and brace-
    balanced ranges.
  - `hover` — markdown card: kind, name, qualified name, `typed by`,
    literal value via `get_value()`.
  - `definition` — usage name → its declaration; type name → the
    type's definition.
  - `completion` — SysML v2 keywords + all named model elements.
  - FULL text sync; UTF-16 position encoding; lifecycle per spec
    (uninitialized requests rejected, shutdown/exit honored, unknown
    methods get -32601, analyzer failures never crash the session).
- **Editor integrations**: `editors/vscode/sysmlpy-lsp/` — ready-to-
  package VS Code extension (plain JS, vscode-languageclient, `.sysml`
  grammar association, `sysmlpy.serverPath`/`serverArgs` settings);
  `docs/LSP.md` documents Neovim setup (built-in `vim.lsp.config` for
  0.11+ and nvim-lspconfig for 0.8–0.10) and other editors.

New `tests/lsp_test.py` — 37 tests (framing round-trips incl. non-ASCII
and malformed headers, lifecycle guards, diagnostic ranges, all
features, in-memory stdio session, real subprocess run of
`python -m sysmlpy.lsp`). Fast suite now 1054 + 123 conformance.

## v0.64.0 (2026-09-02)

### :white_check_mark: Expression evaluator — pint-bound calc/constraint evaluation (Adoption Roadmap Goal 4)

`analyze()` now goes beyond "is this well-formed": attribute defaults,
``calc`` result expressions and ``constraint`` bodies are **evaluated**
with names resolved against the model's own values (pint
``Quantity``-aware), enabling what-if runs and trade studies.

- **New `sysmlpy.evaluator` module** (exported from the package root):
  - `collect_values(model, bindings=None)` — evaluate every attribute
    default; returns qualified-name (``"Pkg::Part::attr"``) and bare-name
    keys → values (pint Quantities, numbers, booleans, strings).
  - `evaluate_expression(expr, model=None, element=None, bindings=None)`
    — evaluate a standalone expression against a model scope (or
    nothing); bindings override names for what-if runs.
  - `evaluate_calculation(model, calc_name, bindings=None)` — evaluate a
    named ``calc def`` result expression.
  - `check_constraints(model, bindings=None)` — evaluate every
    constraint body → `ConstraintReport` with per-constraint
    PASS/FAIL/ERROR results, `to_text()` and `to_json()`.
- **Supported expression subset**: int/real/string/boolean/null/infinity
  literals; `[unit]` values; `+ - * / % **`; `== != < <= > >=`;
  `and or not` (short-circuit); function calls (`sqrt abs min max floor
  ceil round pow`); feature references through the ownership chain and
  dotted chains (`wheels.mass`) with type fallback (`part w : W` →
  `W`'s values). Unsupported constructs raise a clear
  `UnsupportedExpressionError`.
- **Evaluator works on the raw parser dictionary** (collected into a
  namespace tree, evaluated lazily with memoization and cycle
  detection) — the public-API object tree drops some body content.
- **Parser/grammar fixes needed for evaluation:**
  - `calc def` inside `part def` bodies was silently dropped by the
    visitor (`_visit_nested_definition_element` had no
    calculationDefinition branch) and by `Part.load_from_grammar` —
    calc defs now survive into the object tree and `dump()`.
  - Glued unit expressions (`mass / 4 [kg]` collapsing to one name) are
    split and evaluated in scope, mirroring `const_fold`'s strategy.
- **CLI: `sysmlpy eval FILE...`** — `--expr EXPR [--element QNAME]
  [--set NAME=VALUE ...]` for what-if evaluation, `--constraints` for a
  PASS/FAIL report (exit 1 on any failure), default dumps all attribute
  values. Exit codes: 0 clean, 1 failed constraint / evaluation error,
  2 parse error.

New `tests/evaluator_test.py` — 44 tests. Fast suite now 1017 tests +
123 conformance = 1140 total.

## v0.63.0 (2026-09-02)

### :white_check_mark: SysML v2 JSON interchange (Adoption Roadmap Goal 3)

Models can now be exchanged as JSON in the style of the SysML v2 spec's
JSON partition interchange — a flat ``@graph`` of elements identified by
``@id`` / typed by ``@type`` (the abstract-syntax metaclass name), with
scalar properties inline and structural properties as ``{"@id": ...}``
cross-references:

- **New `sysmlpy.interchange` module** (exported from the package root):
  - `to_interchange(model_or_text)` — export a loaded ``Model`` (from
    `loads()` / `load_files()` / programmatic construction) or fresh
    SysML text to the interchange dict. Element ``@id``s are ``uuid5``-
    derived from tree position, so exporting the same model twice yields
    byte-identical JSON (diff-friendly — feeds roadmap Goal 8).
  - `from_interchange(document_or_json_text)` — rebuild a live ``Model``
    from an interchange document. Lossless: the rebuilt model's text
    (``dump()``), grammar-object tree, and traceability report are all
    identical to the original.
  - `interchange_to_json_text(document, indent=2)` — serialization
    helper.
- **Fidelity guarantee:** export flattens the *raw parser dictionary*
  (via the canonical ``dump()`` text), not the grammar classes'
  ``get_definition()`` serialization — the latter normalizes the tree
  (adds ``ownedRelationship`` keys, unwraps ``OccurrenceUsageElement``),
  which changes class re-dispatch on import (satisfy wrappers were
  silently lost before this was caught by the traceability round-trip
  test).
- **`Model._load_definition()`** extracted from `Model.load` — the
  dict→model construction path is now shared by fresh parses and the
  interchange importer.
- **CLI:**
  - `sysmlpy export FILE [FILE...] [-o OUT.json] [--compact] [-l LIBRARY]`
    — load files as one merged model, emit the interchange JSON (exit 2
    on parse failure).
  - `sysmlpy import FILE.json [-o OUT.sysml]` — rebuild the model and
    print or write the equivalent SysML v2 text (exit 2 on invalid
    input; cycle and dangling-reference detection).
- `sysmlpy parse FILE --json` still emits the internal dict; `export`
  is the spec-style exchange format.

New `tests/interchange_test.py` — 38 tests (document shape, deterministic
ids, scalar/null handling, no dangling references, lossless round-trips
incl. traceability interop, error handling, CLI). Fast suite now 973
tests + 123 conformance = 1096 total.

## v0.62.0 (2026-09-02)

### :white_check_mark: Requirement traceability & verification coverage (Adoption Roadmap Goal 2)

The satisfy / verify / verification relationships now parse, round-trip,
and feed a new traceability reporting module:

- **Parser / grammar:**
  - `verification def` definitions and package-level
    `verification <name> : <Type>;` usages parse and round-trip (the
    usage dispatch was previously missing; new
    `RequirementVerificationMember` grammar class).
  - `verify` members inside requirement bodies round-trip in both legal
    forms — reference (`verify massCheck;`) and inline declaration
    (`verify requirement v2 : VDef;`) — via the new
    `VerifyRequirementUsage` grammar class. (Verified empirically: `verify`
    is only legal inside requirement bodies, not verification bodies.)
  - `VerificationCaseDefinition` now dumps keyword `verification def`
    (previously `verification case def`, which did not re-parse) and its
    case bodies are parsed instead of hardcoded empty.
  - Requirement subjects (`subject : Vehicle;` and
    `subject v : Vehicle;`) are extracted as `(name, type)` tuples.
- **Programmatic API:** `Requirement.verified_by` (names from `verify`
  members), `Requirement.subject`, satisfy edges via the existing
  `SatisfyRequirementUsage` grammar wrapper (`.ors` requirement ref,
  `.ssm` subject chain).
- **New `sysmlpy.traceability` module** (also exported from the package
  root):
  - `extract_traceability(model)` builds a `TraceabilityReport` of
    per-requirement `RequirementTrace` records: qualified name,
    documentation text, subject, `satisfied_by` / `verified_by` edges,
    and a computed status (`covered` / `partial` / `uncovered`).
    Undeclared (forward-referenced) satisfy targets still appear in the
    report so edges are never silently dropped.
  - Coverage queries: `coverage()`, `uncovered()`, `unsatisfied()`,
    `unverified()`, `by_name()`.
  - Output: `to_text()`, `to_markdown()`, `to_json()`.
  - `as_traceability_matrix_view(model, output_format=...)` renders a
    requirements × coverage matrix as Markdown, HTML, or PlantUML, with
    `focus` / `elements` filtering, `show_text`, and `style="color"`.
- **CLI:** `sysmlpy trace FILE... [--format text|markdown|json]
  [--fail-on uncovered] [-o FILE] [-l LIBRARY]` — exit 0 clean, 1 when
  uncovered requirements exist under `--fail-on uncovered`, 2 on parse
  failure. Fits the Goal-1 exit-code contract for CI gates.

New `tests/traceability_test.py` — 46 tests covering construct
round-trips, trace extraction, coverage queries, matrix views, and the
`trace` CLI. Fast suite now 957 tests + 123 conformance = 1080 total.

## v0.61.0 (2026-09-02)

### :white_check_mark: CLI: `analyze` + `view` commands with CI-friendly exit codes (Adoption Roadmap Goal 1)

The CLI (`src/sysmlpy/__main__.py`, console script `sysmlpy`) was
restructured into subcommands while **preserving the legacy flat
invocation** (`sysmlpy FILE --dump` etc., including flag-first orders and
its original exit code 1 on file/parse errors):

- **`sysmlpy analyze FILE [FILE...]`** — loads the files as one merged
  model (`load_files`) and runs the semantic analyzer. Human-readable
  output (`error: CODE: message [ref: ...]` lines + summary) or
  `--format json` with a machine-readable issues/summary structure for
  CI integration. Flags: `--fail-on {error,warning,never}` (default
  error), `--no-warnings`, `--no-summary`, `-l/--library`.
- **`sysmlpy view FILE --view NAME`** — renders any of the 11 views
  (`gv`, `pv`, `afv`, `iv`, `stv`, `sv`, `cv`, `tabular`, `datavalue`,
  `matrix`, `browser`) to stdout or `-o FILE`. Flags: `--focus` (element
  name; typos fail with exit 1 instead of silently rendering everything),
  `--element` (repeatable), `--style bw|color`, `--direction TB|LR`,
  `--format plantuml|markdown|html` (tabular views), `-l/--library`.
  View kwargs are filtered by introspection, so graph-only flags are not
  passed to tabular views and vice versa. A failing view (e.g. the
  pre-existing `as_sequence_view` state-body bug) is reported as an
  error message with exit 1, not a traceback.
- **`sysmlpy parse FILE`** — the legacy parse behavior as a first-class
  subcommand (`--dump`, `--json`, `--python`, `-l`).
- **`sysmlpy format FILE...`** (alias `fmt`) — the `-i` / `--check`
  behavior, extended to multiple files.
- **Exit code contract** (documented in `--help`): 0 = success/clean,
  1 = findings at or above the failure threshold / operational error,
  2 = parse or load failure. `--version` added.

New `tests/cli_test.py` — 39 tests covering all subcommands, exit codes,
JSON output, multi-file merged analysis, output files, focus validation,
legacy backward compatibility, and real subprocess invocations of the
module entry point.

Recorded the **Adoption Roadmap** (goals 1–10) in
`docs/DEVELOPMENT_PLAN.md` §6 and `TODO.md`; Goal 1 is now complete.

## v0.60.0 (2026-09-02)

### :white_check_mark: Feature chain type resolution (STATUS.md Medium Priority)

Two semantic-engine fixes for feature chains, both found by probing the
four STATUS.md Medium Priority items:

**1. False-positive `INCOMPATIBLE_FEATURE_CHAIN` on qualified type names.**
`ReferenceCollector` collected typing references (``attribute mass:
ScalarValues::Real``) alongside feature chains, and the chain check treated
the qualified name as ``feature ScalarValues of Real`` — reporting an error
on **every** model that used a namespace-qualified type (library or
user-defined).  Fix:

- `ReferenceCollector` now tags each reference with its relationship kind
  (`typing` / `subsetting` / `redefinition` / `subclassification`) as a
  4th tuple element.
- `_check_feature_chaining_compatible` only chain-checks `subsetting` and
  `redefinition` references — their targets are genuinely feature chains
  (``a::b`` / ``a.b``).  Typing and subclassification references are type
  paths validated by the existing symbol-resolution pass.

**2. Full dotted-chain resolution through declared types.**
Expression chains like ``wheels.hub.mass`` previously only navigated
structural children; when a segment lives on the current element's
*declared type* (e.g. `hub` on `part def Wheel`, the type of `wheels`),
resolution failed with `UNRESOLVED_EXPRESSION_IDENTIFIER`.  Fix in
`SemanticAnalyzer._resolve_feature_chain`:

- The walk now tracks the current navigation *type* alongside the current
  element (seeded from the head's declared type).
- When structural child navigation fails, the segment is resolved as a
  member of the type definition via `SymbolTable._definition_features`,
  following subsetting inheritance (`find_defining_type_for_feature`) and
  qualified type names (`ScalarValues::Real` → simple-name fallback).
- Works in attribute defaults and constraint bodies.

Tests: 17 cases in `tests/semantic_test.py`
(`TestFeatureChainTypeResolution`).

**3. Members of an enclosing usage's declared type are now visible.**
Members of a usage's type are inherited features of the usage, so chained
references inside a usage body must resolve against them:

```
part myCar : Car {
    attribute carPower :> engine::power;   // engine is a member of Car
}
```

previously raised `UNDEFINED_SYMBOL` for `engine::power` (and the `.`
expression-chain variant likewise) because the head lives in `Car`'s
symbol-table scope — a *sibling* of the referencing scope, unreachable by
upward lookup.  Fix:

- `SemanticAnalyzer._resolve_through_context` resolves a chained (or
  single) reference by looking the head up as a feature of the declared
  type of each enclosing usage (innermost first,
  `_context_types_for_resolution`), then walking the remaining segments
  through declared types (`_walk_chain_segments`).  Strictly
  existence-based — every segment must resolve, so typos still error.
- Wired into the symbol-resolution pass (Step 4) and the expression
  identifier pass (Step 4b); `engine::name` (nonexistent member) is still
  reported by both passes.
- Chain-compatibility fix: after locating an *inherited* chain feature,
  the loop now advances to the feature's *declared type* instead of the
  supertype that declares it (`engine` declared on `Vehicle`, typed by
  `Engine` means the next segment is checked against `Engine`, not
  `Vehicle`), mirroring the direct-feature branch.

Covered: false-positive regressions for library and user-qualified types,
chain resolution through typed features (attribute defaults + constraint
bodies), inheritance through `:>`-subclassed part types, context-type
resolution for `::` / `.` / single-member references in usage bodies,
inherited-member chains, and negative cases (bad middle/tail segment,
unknown head, package-level undefined still flagged).
Suite: 170 semantic tests, 850 fast-suite tests, 123 conformance tests pass.

## v0.59.0 (2026-08-31)

### :white_check_mark: Top-level attribute multiplicity — verified fixed, flags bug found & fixed

Investigation of the last STATUS.md High Priority item found the headline
bug **already resolved in v0.40.0** (commit `eb65e9e` switched the top-level
`attributeUsage` dispatch from the typed-by-only `_build_specialization()`
to `_build_full_specialization_from_ctx()`, which captures multiplicity via
`_get_multiplicity_part()`); the STATUS / PROJECT_SUMMARY / AGENTS.md
entries were simply never cleared.  Verified end-to-end: bounds (`[N]`,
`[N..M]`, `[*]`, variable refs) survive for `attribute`, `part`, `item`,
and `port` at package level, with typing and/or re-declarations.

However, the investigation surfaced a **real adjacent bug**:

- `ordered` / `nonunique` multiplicity flags were **hardcoded `False`** in
  both ANTLR multiplicity extractors (`_get_multiplicity_part`,
  `_extract_multiplicity_from_mp`), silently dropping `attribute x[3]
  ordered;`'s keyword.
- After fixing the visitor, a **second** bug surfaced in
  `MultiplicityPart.dump()` (`grammar/classes.py`): its
  `isOrdered and not isOrdered2` guard never fired because `__init__`
  populates both fields from the same dict value — `ordered` was dropped on
  every round-trip while `nonunique` happened to work.

Fixes:
- Both visitor multiplicity extractors now read `ORDERED()` / `NONUNIQUE()`
  from the ANTLR `MultiplicityPartContext`.
- `MultiplicityPart.dump()` emits the keyword when either flag is set.
- Grammar note: `nonunique ordered` canonicalizes to `ordered nonunique`
  (grammar-rule order; semantically identical) — round-trip is stable.
- 7 regression tests in `tests/class_test.py` (flags, bounds, all usage
  kinds, canonicalization stability).

## v0.58.0 (2026-08-31)

### :white_check_mark: Import / AliasMember source-order preservation (High Priority fix)

`Model.load()` and `Package.load_from_grammar()` always preserved
`Import` / `AliasMember` grammar nodes in the body, but both
`_ensure_body()` rebuild paths (Model, definition.py:170; Package,
definition.py:567) serialized children first and appended imports and
aliases at the **end** — so any source file interleaving imports with
definitions failed exact-text round-trip through the public API
(`loads(...).dump()` reordered statements).

- Both `_ensure_body()` implementations now use the existing grammar body
  as an **ordering template**: `Import` / `AliasMember` nodes are re-emitted
  at their original positions, `PackageMember` slots are refilled with
  fresh serializations of the public children in order, children added
  programmatically (or beyond the recorded slots) append at the end, and
  children removed programmatically drop their stale slots.
- Root-level imports (before the first package) round-trip as well.
- `add_import()` programmatic behavior unchanged (appends at end).
- 10 new regression tests in `tests/import_test.py`
  (`TestImportSourceOrder`): before/after/interleaved imports, multiple
  imports, aliases before/after members, mixed import+alias, nested
  packages, programmatic add, and dump-loop idempotence.

### :memo: Notes

- Visitors and grammar classes already handled `Import` / `AliasMember` —
  this fix is confined to the two `_ensure_body()` rebuild paths in
  `definition.py`; parse conformance and grammar round-trip unaffected
  (143/143 grammar, 123/123 conformance expected).
- STATUS.md "AliasMember / Import handling" high-priority item resolved;
  the node types were already supported end-to-end — the gap was
  serialization ordering only.

## v0.57.0 (2026-08-31)

### :white_check_mark: Typed-By Preservation on `load_from_grammar` (High Priority fix)

Previously only `Action` captured its typing from the grammar; every other
usage kind (`Part`, `Item`, `Attribute`, `Port`, `Connection`, `Interface`,
`UseCase`, `Requirement`, `State`, ...) loaded via `loads()` lost the
`: TypeName` relationship on the **public-API object** (the grammar object
kept it, so text round-trip still worked).

- `_extract_specialization_info()` hoisted from `Action` to base `Usage` and
  extended to handle **both** grammar layouts: usage-style
  (`grammar.usage.declaration.declaration.specialization` — PartUsage,
  AttributeUsage, ItemUsage, PortUsage, ...) and behavior-style
  (`grammar.declaration.declaration*.specialization` — ActionUsage, ...).
  Captures `Typings` (`: Type`), `Subsettings` (`:> base`), `Redefinitions`
  (`:>> base`), and `References` (`::> base`) names.
- Base `Usage.__init__` now initializes `_typed_by_name`,
  `_specializes_names`, `_redefined_refs`, `_referenced_refs` for all
  subclasses.
- Extraction wired into `Usage.load_from_grammar` (base) plus the
  overriding loaders `Interface`, `UseCase`, `Requirement`, and `State`,
  and into `_load_behavior_child()` for `Constraint`, `Calculation`,
  `State`, `Requirement`, and `Allocation` usages inside definition bodies.
- New public property **`Usage.typed_by_name`** — the declared type as a
  name string (`part engine : Engine` → `"Engine"`;
  `attribute mass : ScalarValues::Real` → `"ScalarValues::Real"`); `None`
  when untyped. Resolving `typedby` to the definition *object* via a model
  pass remains a follow-up.
- 7 new regression tests in `tests/class_test.py` (all usage kinds,
  qualified names, behavior children, unset default, dump round-trip
  unchanged).

### :memo: Notes

- `set_value()` unit validation now sees the typed type name on elements
  loaded from grammar (previously it silently skipped because `typedby`
  was only populated programmatically).
- Known-issue entries in `STATUS.md`, `docs/PROJECT_SUMMARY.md`, and
  `AGENTS.md` updated; examples' "typedby may not be populated" comments
  corrected.

## v0.56.0 (2026-08-31)

### :rocket: Phase D — High-Performance Parsing & Graph Store Queries

**Two-stage SLL → LL parsing** (`/antlr_parser.py`): `parse()` now runs
the ANTLR prediction in fast **SLL** mode first and falls back to the
full-context **LL** pass only when the SLL attempt fails.  For valid
input the tree is produced in a single parser build; for invalid input
the fallback reproduces the error at the same source position (message
wording can differ between prediction modes — e.g. "missing '}' at
'<EOF>'" vs "extraneous input '<EOF>' expecting {...}").  New
`prediction_mode=` parameter: `"sll"` (default, two-stage), `"ll"`
(force full-context), `"sll_only"` (no fallback).

Benchmark (6,000-element model, warmed DFA cache): parse-only time
**4.92 s (SLL) vs 7.89 s (LL) — 38&nbsp;% faster**.  Cold first parse
also carries a one-time ANTLR DFA-construction cost (~5 s) shared
across all subsequent parses in the process.  End-to-end `loads()` on
a 4,002-element model: 9.0 s.

**Graph query extensions** (`store.py`):

- `NetworkXStore.all_paths(src, dst, rel_type=None, max_paths=20)` —
  enumerates simple paths for impact/routing analysis
- `NetworkXStore.descendants_depth_limited(root, max_depth)` —
  hierarchy-level queries ("direct children of this level")
- `NetworkXStore.neighborhood(id, radius)` — ego-graph in both
  directions
- `NetworkXStore.impact_analysis(id, rel_types, direction)` —
  transitive downstream/upstream blast-radius
- `NetworkXStore.in_degree_centrality / out_degree_centrality` —
  hub detection per direction
- `KuzuStore.execute_cypher(query)` — raw Cypher passthrough returning
  rows as dicts (node values flattened to id/name/sysml_type;
  path node lists flattened to id lists)
- `KuzuStore.shortest_path_between_named(a, b)` — hop-by-hop expand
  (Kùzu has no `shortestPath()` builtin)
- `KuzuStore.siblings(id)` — structural siblings
- `KuzuStore.hub_elements(min_degree, direction)` — outgoing/incoming/
  both degree hubs

19 new tests (`tests/two_stage_parse_test.py` 7, `tests/store_test.py`
+12).  Full suite: **809 fast + 123 conformance passed.**

## v0.55.0 (2026-08-31)

### :balance_scale: Phase C — Expression Type Checking & Unit Safety

Operator operand-type compatibility and pint unit-dimension safety now
run as analyzer step 4c (`SemanticAnalyzer._check_expression_types`):

- **Operator rules** — `OPERAND_TYPE_MISMATCH` errors for:
  - logical (`and`/`or`/`xor`/`implies`/`not`) with non-boolean operands
  - relational (`< > <= >=`) with unordered (boolean) operands
  - equality (`==`/`!=`) comparing boolean with non-boolean
  - arithmetic with string/boolean mismatches (`"a" + 5`, `flag * 2`)
- **Unit dimensions** — `UNIT_DIMENSION_MISMATCH` errors when `+`/`-`
  combine different ISO-80000 dimensions (adding `[m]` to `[kg]`).
  Dimensionless `+ quantity` and `*`/`/` of any dimensions are allowed.
  Dimensions are extracted from the bundled ISQ library's
  `quantity dimension:` annotations (~560 value/unit types indexed,
  alias-aware).
- **Constant folding** — new `const_fold(expr_dict)` utility statically
  reduces deterministic literal expressions (`2 + 3 * 4` → `14`,
  `2 ** 10` → `1024`, `-(2-5)` → `3`) with a restricted safe arithmetic
  evaluator for parenthesized text forms; non-numeric operands return
  `None`.

Structured boolean-keyword emission (prerequisite fix): `and`, `or`,
`xor`, `implies` operators were previously collapsed to glued text
(`aandb`) by the visitor — they now emit structured
`And/Or/Xor/Implies-Operand` dicts and the grammar classes render them
on round-trip (`a and b`, `a or (b and c)` survive
parse→dump→parse). `**`/`^` exponentiation now also splits instead of
gluing text. Boolean literals `true`/`false` capture as
`LiteralBoolean` primary nodes (new grammar class) so type checking can
classify them.

Operand typing resolves each identifier to its declared type
(`ScalarValues::Integer`, `ISQ::MassValue`, …) through the Phase B
scope machinery; comparison chains (`n > 3 and n < 10`) classify as
boolean results.

Scope notes: `*`/`/` dimension derivation (e.g. `mass * speed !=
ForceValue` inference) and unit-conversion folding are Phase D scope;
multiplication is only checked for non-numeric operand categories.

17 new tests in `tests/semantic_test.py` (153 total).
Full suite: **836 passed** (incl. 143 grammar round-trip + 123
conformance).

## v0.54.0 (2026-08-30)

### :mag: Phase B — Name Resolution on Structured Expressions

The semantic analyzer now walks the structured expression ASTs captured
since v0.52.0 and resolves every identifier against the symbol table.
A new analyzer step (4b in `SemanticAnalyzer.analyze`) collects
identifiers from expression bodies and emits
`UNRESOLVED_EXPRESSION_IDENTIFIER` errors for names that don't resolve.

Covered expression contexts: constraint / assert-constraint bodies,
calculation result expressions, attribute / item / port / reference
default values (`= expr`), and transition guard expressions.

Resolution rules, in order:

- qualified names (`P::A`, `ScalarValues::Real`) against package
  namespaces and the `LibrarySymbolIndex`
- unqualified names against the local scope chain (enclosing
  definitions, imports, inherited features)
- dotted feature chains (`wheel1.hub.mass`) resolved segment by
  segment: the head must resolve as a symbol from the referencing
  scope, and each subsequent step must exist within the previous
  step's element subtree
- invocation targets (`size(edges)`) resolve like any other reference;
  argument expressions are walked recursively

Library index fix: `_DEFINITION_RE` now captures `function` declarations
(`function size { ... }` in `CollectionFunctions.kerml` etc. — ~40+
library functions newly indexed), and `SemanticAnalyzer._normalize_library_paths(None)`
resolves to the bundled library root instead of an empty list that
poisoned the symbol-index cache with the hardcoded fallback set.

New public internals in `semantic.py`:
`ExpressionIdentifierCollector`, `_walk_expression_identifiers()`,
`_find_owned_expressions()`, `SemanticAnalyzer._check_expression_identifiers()`,
`SemanticAnalyzer._resolve_feature_chain()`, `SemanticAnalyzer._find_member()`.

Phase C next (v0.55.0): operand type checking and pint unit-dimension
compatibility inside expressions — see
[docs/DEVELOPMENT_PLAN.md](docs/DEVELOPMENT_PLAN.md).

Test results: fast suite 696/696, grammar round-trip 143/143.
12 new expression-resolution tests in `tests/semantic_test.py` (136 total).

## v0.53.1 (2026-08-30)

### :white_check_mark: Phase A — Grammar Class Integrity & 100% Parse Conformance

All 358 grammar classes in `src/sysmlpy/grammar/classes.py` now implement
`get_definition()` (verified by reflection audit — 36 were missing). The
complete list of additions: `ActionBodyItemTarget`, `AdditiveOperand`,
`AnnotatingMember`, `AssignmentNode`, `BodyExpression`, `ChangeExpression`,
`ChangeExpressionMember`, `ChangeResultExpressionMember`,
`ConjugatedPortTyping`, `DefinitionExtensionKeyword`, `DefinitionPrefix`,
`EffectBehaviorUsage`, `EqualityExpressionMember`,
`EqualityExpressionReference`, `ExpressionBody`, `ExpressionBodyMember`,
`FeatureChainPrefix`, `IndividualUsage`, `ItemFeature`, `ItemFeatureMember`,
`MultiplicitySourceEnd`, `MultiplicitySourceEndMember`, `NamedArgument`,
`NamedArgumentList`, `NamedArgumentMember`, `OwnedExpressionMember`,
`ParameterRedefinition`, `PayloadFeatureSpecializationPart`,
`ReferenceTyping`, `ReturnParameterMember`, `StructureUsageMember`,
`Succession`, `TriggerExpression`, `TriggerFeatureValue`, `TriggerValuePart`.

Round-trip bugs fixed along the way:

- `ReturnParameterMember.get_definition()` emitted `ownedRelatedElement`
  as a list; `UsageElement.__init__` (and the visitor) expect a single
  dict. `loads()` on models with calc `return` members
  (`simpletests/AssignmentTest.sysml`) previously raised
  `TypeError: This does not seem to be valid.`
- `MultiplicitySourceEnd` only kept the last `OwnedMultiplicity` child;
  now accumulates all children like its siblings.

XPect parse conformance is now **123/123 (100%)**:

- `Import_Visibility_Valid.error` updated to expect the
  `extraneous input 'import'` syntax error the corrected grammar raises
  on a bare import (imports require explicit visibility per the
  normative OMG spec).

Test results: fast suite 684/684, grammar round-trip 143/143, XPect
conformance 123/123.

## v0.53.0 (2026-08-28)

### :sparkles: Per-precedence expression grammar + structured cascade emit

The vendored SysML v2 grammar is regenerated from the upstream
`daltskin/sysml-v2-grammar` with the per-precedence cascade
implemented properly. v0.52.0's precedence-climbing pass is
obsolete and replaced by a direct walker over the new grammar's
precedence levels (`nullCoalescing -> ... -> primary`).

Also fixed: `xor`/`and` precedence order. The OMG XText reference
grammar has `implies < or < xor < and < equality` (and binds tighter
than xor); the daltskin generator's `OPERATOR_PRECEDENCE` table
and per-level list had them swapped. `a xor b and c` now parses as
`a xor (b and c)` instead of `(a xor b) and c`.

Two visitor/class bugs fixed:

- `first` keyword was dropped from guarded transitions when no
  usage declaration was given; the grammar allows `transition first A if c then B;`
- `render` usage bodies (doc, comment, ...) were dropped on
  round-trip; the visitor previously stubbed the body empty
- `UnaryExpression.dump()` now renders prefix operators
  (`-x`, `not flag`)

Six grammar tests rewritten from non-standard syntax
(`guard`, `render state X { shape box; color ...; annotation "..."; }`)
to OMG-standard forms (`if`, `render X { doc /* ... */; comment about X /* ... */; }`).
The old syntax only existed in sysmlpy's hand-patched vendored
grammar; the OMG grammar has no such keywords.

### :test_tube: Test results

- **143/143** grammar tests pass (was 130/143 with the prior grammar)
- **144/144** class/main/repr/navigate tests pass
- **310/310** official OMG conformance files parse via the
  companion `daltskin/sysml-v2-grammar` repo (was vacuously
  passing before -- the conformance runner had three bugs that
  silently passed every file without actually parsing it; those
  were fixed in a separate commit on the daltskin side)

## v0.52.0 (2026-08-27)

### :sparkles: Phase 1 expression-capture: implementation shipped

Phase 1 of `docs/v0.46.0_expression_capture_plan.md` lands. The
visitor now emits a structured expression dict with operators
captured at the correct layer, enabling a future name resolver
to walk identifiers individually. The key insight: the vendored
SysML v2 grammar lists all binary operators in the same
`ownedExpression` rule with equal precedence, so ANTLR
left-associates and produces a non-precedence-respecting parse
(e.g. `a + b * c` parses as `(a+b) * c`). The implementation
runs a precedence-climbing pass on the ANTLR children list to
re-arrange operators by binding power before emitting the
structured chain.

### :test_tube: Test results

- **143/143** grammar tests pass (5m 30s; 10 phase1 tests +
  132 non-phase1 including the 53 Training-suite tests that
  were at risk due to the precedence-climbing refactor)
- **144/144** class/main/repr/navigate tests pass
- **124/124** semantic tests pass
- **72/72** import/validator/project tests pass
- **19/19** boxes_view tests pass
- **118/123** conformance tests pass (same 5 pre-existing
  failures as the v0.51.0 baseline — no new regressions)

### :white_check_mark: Test coverage

- **10 Phase 1 regression tests** (added in v0.52.0-pre
  failing-first commit, all now passing):
  - `test_expression_capture_binary_equality_v046_phase1` —
    `a == b` emits `EqualityExpression.operation[0]` with
    `operator='=='`, `operand.name='ClassificationExpression'`.
  - `test_expression_capture_invocation_v046_phase1` —
    `size(edges) == 18` emits `InvocationExpression` for
    `size(edges)` plus `EqualityExpression` for `== 18`.
  - `test_expression_capture_feature_chain_v046_phase1` —
    `wheel1.mass > 0` preserves the feature chain and
    `RelationalExpression` for `> 0`.
  - `test_expression_capture_arithmetic_precedence_v046_phase1` —
    `a + b * c == 0` captures all three operators (`+`, `*`,
    `==`) in the structured output.
  - `test_expression_capture_unary_minus_v046_phase1` —
    `-x == 0` emits `UnaryExpression.operator='-'`.
  - `test_expression_capture_not_operator_v046_phase1` —
    `not flag == true` emits `UnaryExpression.operator='not'`.
  - `test_expression_capture_logical_and_v046_phase1` —
    `a and b` confirms `AndExpression` layer is present
    (and/or/xor/implies fall back to text preservation
    because the grammar class uses list-based operand/operator
    fields that don't fit the chain layout — documented
    limitation).
  - `test_expression_capture_logical_or_v046_phase1` —
    same as above for `OrExpression`.
  - `test_expression_capture_conditional_ternary_v046_phase1` —
    confirms `ConditionalExpression` layer is present in the
    chain shape (the grammar's `IF ? :` ternary form is not
    currently parseable inside `calc` bodies — known grammar
    limitation).
  - `test_expression_capture_range_v046_phase1` —
    `0..n` emits `RangeExpression.operator='..'`.
  - `test_expression_dict_not_collapsed_v046_phase1` —
    structural test: the visitor does NOT collapse
    `radius == zero` into a single `FeatureReferenceMember` with
    `names=['radius==zero']`; the two identifiers are
    separately addressable.

### :wrench: Internal changes

- **Added precedence-climbing pass** to `_emit_structured_expression`
  in `src/sysmlpy/antlr_visitor.py`:
  - `_PRECEDENCE_RANK` map (operator → binding power)
  - `_OPERATOR_TO_LAYER` map (operator → grammar class layer)
  - `_find_split_index` (find lowest-precedence operator in
    ANTLR children, handling left-associative same-precedence
    and right-associative `**`/`^`)
  - `_build_binary_chain` (recursively emit LHS/RHS, splice op)
  - `_splice_operator` (insert op at the correct chain layer)
  - `_add_op_to_layer` (handle re-arrangement when LHS has a
    lower-precedence top op)
  - `_embed_layer_at_path` (preserve rhs's higher-layer ops
    after re-arrangement)
  - `_unwrap_to_layer` (return the rhs sub-dict matching the
    grammar class's operand type expectation)
  - `_embed_rhs_higher_ops` (preserve rhs's operators at higher
    layers when splicing)
  - `_is_owned_chain` / `_walk_chain` / `_LAYER_PATHS` /
    `_LAYER_OP_FIELDS` helpers
  - `_build_invocation_primary` / `_build_arg_list_dict` (emit
    `InvocationExpression` for `Function(args)` pattern)
  - `_make_feature_reference_chain` (multi-part qualified name
    with `::` separator; `a.b` field access falls back to text
    to preserve round-trip — `FeatureChainExpression` grammar
    class not yet implemented)
- **Fixed AdditiveOperand.dump** in `src/sysmlpy/grammar/classes.py`:
  - was `"" .join([operator, operand.dump()])` (no space);
    now `" ".join([operator, operand.dump()])` to match the
    other Operand.dump implementations and produce correct
    spacing in round-trip output.
- **Added `get_definition()` methods** to the argument grammar
  classes (InvocationExpression, ArgumentList,
  PositionalArgumentList, ArgumentMember, Argument,
  ArgumentValue) so `load_from_grammar` can re-emit the dict.

## v0.51.0 (2026-08-26)

### :white_check_mark: Test coverage

- **Added three regression tests contributed by
  [PR #7](https://github.com/mycr0ft/sysmlpy/pull/7) by @jman4162** —
  the underlying fix for issue #4 (dependency statements) is already
  shipped in v0.46.0, but PR #7 brought three useful tests:
  - `test_dependency_qualified_endpoints_split_regression_gh4_pr7` —
    dotted `Sub::Client` qualified-name endpoints reach the dict
    as multi-element `names` lists.
  - `test_dependency_named_multi_client_supplier_regression_gh4_pr7` —
    `dependency Use from Client1, Client2 to Supplier1;` round-trips
    with the correct identification and split endpoint lists.
  - `test_dependency_bare_round_trip_regression_gh4_pr7` — the bare
    `dependency b to A;` form produces a `clients` list with a single
    entry (not collapsed into a string), matching the `Dependency`
    grammar-class contract.

  PR #7 is closed as superseded — v0.46.0 already shipped the
  underlying fix; this release is purely additional regression
  coverage. (Note: PR #7 emits ``client``/``supplier`` singular keys
  whereas this codebase uses plural ``clients``/``suppliers`` to
  match the `Dependency` grammar class. We keep the plural form.)

### PR review notes (post-v0.51.0)

- **[PR #9](https://github.com/mycr0ft/sysmlpy/pull/9) by @jman4162** —
  `Surface braced metadata body features in the ANTLR dict`. Same
  issue (#8) as v0.49.0, simpler implementation: emits a list of
  raw-text strings (`elem.getText()`) instead of v0.49.0's structured
  dicts (with `name`, `value`, `text`, `featureKeyword`, `redefines`,
  `specialization`). **Closed as superseded** — v0.49.0 is strictly
  more comprehensive (structured per-element dicts, plus the
  heterogeneous-alternative path for `definitionMember |
  metadataBodyUsageMember | aliasMember | importRule`, plus the
  `MetadataFeature` grammar class round-trip). v0.49.0's structured
  dicts are a strict superset of PR #9's raw-text strings: the
  `text` field of each entry equals `elem.getText()`.

## v0.50.0 (2026-08-26)

### :bug: Bug Fixes / :twisted_rightwards_arrows: PR alignment

- **Allocated `AllocationUsage.connectorPart` → `AllocationUsage.part`**
  to align with [PR #6](https://github.com/mycr0ft/sysmlpy/pull/6)
  by @jman4162 and the existing `ConnectionUsage` convention. The
  v0.47.0 fix (issue #5) introduced `connectorPart` as the dict key,
  which diverged from the codebase's existing `part` field on
  `ConnectionUsage`. PR #6 surfaced that divergence; this release
  adopts the standard shape so downstream consumers (e.g. sysml2kit)
  can read both connector-bearing usages with the same code path.
  Fix:
  - `_make_allocation_usage_dict` (`antlr_visitor.py`) now emits the
    connector dict under the `part` key, matching `ConnectionUsage`.
  - `AllocationUsage` (`grammar/classes.py`) now reads `definition["part"]`
    in `__init__` (the legacy `definition["connectorPart"]` is still
    accepted as a back-compat fallback) and round-trips via
    `get_definition()` under `part`. Dump format unchanged.
  - `tests/grammar_test.py::test_allocation_dict_has_connector_part_gh5`
    updated to assert the new `part` key.
  - Added `test_allocation_dotted_endpoints_regression_gh5_pr6`
    (new coverage contributed by PR #6: `allocate A to t.array;`
    feature-chain endpoint round-trip).

  PR #6's three tests (`test_allocate_endpoints_survive`,
  `test_named_allocation_still_parses`,
  `test_allocate_dotted_endpoints`) all pass against this
  release. PR #6 is being closed as superseded.

  Tests: 438/438 fast pass; 118/123 conformance (same 5 pre-existing
  failures byte-identical to baseline).

## v0.49.0 (2026-08-26)

### :bug: Bug Fixes

- **Braced metadata bodies lose their feature values
  ([issue #8](https://github.com/mycr0ft/sysmlpy/issues/8)).**
  `_visit_metadata_feature_dict` only captured the raw body text
  (`ctx.metadataBody().getText()`) for a braced body. The individual
  `key = value;` assignments inside the body were unreachable from
  the dict, so any consumer of `load_grammar_antlr` had no way to read
  the feature assignments without re-parsing the raw text.
  Fix:
  - `_visit_metadata_feature_dict` (`antlr_visitor.py`) now emits
    a `bodyFeatures` list alongside the raw `body` text. Each entry
    carries `name` (feature name from `ownedRedefinition`),
    `value` (raw `=value` text from `valuePart`), `text` (full
    source text of the element), `featureKeyword` (whether `feature`
    was used), `redefines` (whether `redefines` was used), and
    `specialization` (`: Type` text if present).
  - New `_visit_metadata_body_features` and
    `_visit_metadata_body_element` helpers in `antlr_visitor.py`
    walk each `metadataBodyElement` and produce one structured
    entry. The heterogeneous alternative
    (`definitionMember | metadataBodyUsageMember | aliasMember |
    importRule`) is captured as raw-text fallback entries.
  - `MetadataFeature` (`grammar/classes.py`) now stores
    `bodyFeatures` as a list attribute and round-trips it through
    `get_definition()`. The raw `body` text continues to drive
    `dump()` so whitespace is preserved exactly.
  - The `;` (SEMI) form still emits `bodyFeatures: []` (an empty
    list) so consumer code can iterate unconditionally.

  Regression tests in `tests/grammar_test.py::*regression_gh8*`:
  - `test_metadata_braced_body_features_regression_gh8`
  - `test_metadata_braced_body_round_trip_regression_gh8`
  - `test_metadata_semi_body_features_empty_regression_gh8`
  - `test_metadata_redefines_in_body_regression_gh8`
  - `test_metadata_specialization_in_body_regression_gh8`

### Known issue NOT addressed

- `metadata Classified { ... }` *inside a `ref x { ... }` body*
  still goes un-extracted (the `ref`'s `UsageCompletion` body isn't
  walked for `metadata` applications). Same root cause as the
  pre-existing `assert constraint` inside `part def` body bug,
  which v0.48.0 Phase 0 fixed for definitions but not yet for
  usages. Tracked as a follow-up.

## v0.48.0 (2026-08-26)

### :bug: Bug Fixes

- **Phase 0 of
  [docs/v0.46.0_expression_capture_plan.md](docs/v0.46.0_expression_capture_plan.md)**:
  usage kinds inside a `part def` / `item def` body now survive
  `Part.load_from_grammar` into the public-API tree. Before this fix,
  `assert constraint`, `constraint`, `calc`, `state`, `action`,
  `requirement`, `satisfy requirement`, and `allocate` usages
  *inside a definition body* were silently dropped — only the
  grammar tree retained them, so `model.dump()` emitted an empty
  body. Same root cause as issue #3 finding 4 (constraint body name
  resolution is impossible without the expression reaching the model
  tree first). Fix:
  - `_visit_nested_occurrence_usage` (`antlr_visitor.py`) now
    dispatches `stateUsage` and `allocationUsage` inside a
    `BehaviorUsageElement`; `allocationUsage` inside a
    `StructureUsageElement` is also dispatched. Both unwrap the
    `PackageMember` outer wrapper so the body builder sees the
    expected `OccurrenceUsageElement`.
  - `Usage.load_from_grammar` (`usage.py`) now handles the missing
    `BehaviorUsageElement`, `InterfaceUsage`, and `AllocationUsage`
    branches in its children dispatch (the new `BehaviorUsageElement`
    branch delegates to a new module-level helper
    `_load_behavior_child`).
  - The orphan `add_directed_feature` method (pushed out of `Usage`
    during the edit) was restored as the last method of `Usage`,
    re-fixing the four `test_port_directed_*` regressions that
    appeared mid-edit.

  Regression tests in `tests/grammar_test.py::*v046_phase0*`:
  - `test_assert_constraint_survives_part_def_load_v046_phase0`
  - `test_constraint_usage_survives_part_def_load_v046_phase0`
  - `test_calculation_usage_survives_part_def_load_v046_phase0`
  - `test_state_usage_survives_part_def_load_v046_phase0`
  - `test_action_usage_survives_part_def_load_v046_phase0`
  - `test_requirement_usage_survives_part_def_load_v046_phase0`
  - `test_satisfy_requirement_survives_part_def_load_v046_phase0`
  - `test_allocation_survives_part_def_load_v046_phase0`
  - `test_interface_usage_survives_part_def_load_v046_phase0`
  - `test_assert_constraint_survives_item_def_load_v046_phase0`

  Tests: 432/432 fast pass; 118/123 conformance (same 5 pre-existing
  failures byte-identical to baseline).

## v0.47.0 (2026-08-26)

### :bug: Bug Fixes

- **`allocate A to b;` lost its connector endpoints
  ([issue #5](https://github.com/mycr0ft/sysmlpy/issues/5)).**
  `_make_allocation_usage_dict` (`antlr_visitor.py:7925`) built the
  `AllocationUsage` dict carrying only identification — the
  `connectorPart` from `allocationUsageDeclaration` was silently
  dropped before the dict existed, breaking downstream traceability
  for `allocate X to Y` statements. The same gap affected the n-ary
  `allocate (X, Y, Z);` form (no path at all in
  `_build_connector_part_dict`). Mirrors the `SatisfyRequirementUsage`
  pattern (`ors/ssm`) for connector endpoints. Fix:
  - `_make_allocation_usage_dict` now walks `aud.connectorPart()` and
    emits a `ConnectorPart` dict (binary or nary).
  - `_build_connector_part_dict` now also handles `naryConnectorPart`
    and emits a `NaryConnectorPart` dict.
  - `AllocationUsage` (`grammar/classes.py`) now extends
    `_PrefixedUsageBase` with an optional `connectorPart` field;
    `dump()` renders the connector as `allocate X to Y` (binary) or
    `allocate (X, Y, Z)` (nary) after the optional declaration.
  - New `NaryConnectorPart` grammar class
    (`grammar/classes.py`) and dispatch from `ConnectorPart`.

  Regression tests: `test_allocation_endpoints_bare_regression_gh5`,
  `test_allocation_endpoints_named_regression_gh5`,
  `test_allocation_nary_regression_gh5`,
  `test_allocation_bare_no_connector_still_works_gh5`,
  `test_allocation_dict_has_connector_part_gh5`.

## v0.46.0 (2026-08-26)

### :bug: Bug Fixes

- **Visitor drops dependency statements entirely
  ([issue #4](https://github.com/mycr0ft/sysmlpy/issues/4)).**
  `dependency b to A;` (and every other dependency form) was silently
  dropped at parse time. The `Dependency` grammar class was fully
  implemented in `grammar/classes.py:9758` but no visitor dispatch
  constructed it, and `DefinitionElement.__init__` had no branch for
  it. Fix:
  - `_make_dependency_dict` (`antlr_visitor.py`) emits a Dependency
    dict from the `dependency` ANTLR context, handling both grammar
    alternatives (bare `qn to qn` and `dependencyDeclaration`).
  - `DefinitionElement.__init__` (`grammar/classes.py`) now dispatches
    `Dependency` (also `LibraryPackage`, which was a follow-on gap
    from v0.45.0).
  - `Package.load_from_grammar` (`definition.py`) now constructs a
    public-API `Dependency` instance.
  - `Dependency.dump` (`grammar/classes.py`) emits `from` between an
    identification and its clients; the bare form
    `dependency name a to X;` is unparseable due to ANTLR grammar
    ambiguity (`(identification? FROM)?` can't decide whether `name`
    is identification or the first qualified name without `from`).
  - `Dependency` public-API class added to `usage.py` (and re-exported
    from `__init__.py`).

  Regression tests: `test_dependency_statement_bare_regression_gh4`,
  `test_dependency_named_with_from_regression_gh4`,
  `test_dependency_anonymous_with_from_regression_gh4`,
  `test_dependency_multi_client_supplier_regression_gh4`,
  `test_dependency_definition_element_dispatch_regression_gh4`.

## v0.45.0 (2026-08-26)

### :bug: Bug Fixes

- **Metadata applications with braced bodies no longer silently drop
  their contents ([issue #3](https://github.com/mycr0ft/sysmlpy/issues/3),
  findings 1a/1b).** `@Safety { isMandatory = false; }` previously
  round-tripped as `@ : Safety` because the visitor only captured
  `;` as the body text and discarded every braced body at visit time.
  `_visit_metadata_feature_dict` now preserves the raw body text
  (`getText()`) when the body is `{ ... }`. The `;` form is unchanged.
  Regression tests: `test_metadata_application_braced_body_regression_gh3`,
  `test_metadata_application_semicolon_body_still_works_gh3`.

- **Files that open with `standard library package` now load
  ([issue #3](https://github.com/mycr0ft/sysmlpy/issues/3), finding 2).**
  OMG standard library files (ISQBase.sysml, SI.sysml,
  ISQThermodynamics.sysml, …) raised
  `ValueError: Base Model must be encapsulated by a package.` because
  `_visit_definition_element_dict` had no branch for the
  `libraryPackage` grammar rule (it only matched `package`). A
  `libraryPackage` branch was added that reuses
  `_make_nested_package_dict(..., is_standard_library=True)`. The
  `Package` grammar class now tracks `isStandardLibrary` from the dict
  and emits the `standard library ` prefix in `dump()` so the
  round-trip preserves the original keyword. Regression tests:
  `test_standard_library_package_loads_regression_gh3`,
  `test_standard_library_isqbase_regression_gh3`.

### :memo: Documentation

- Added README scope reminder that a green parse means the file
  *parsed*, not that anything inside a constraint body was checked
  ([issue #3](https://github.com/mycr0ft/sysmlpy/issues/3), reporter's
  suggestion).
- Added a `semantic.py` constraint-body-resolution entry to STATUS.md
  §Known Issues.

### Known issues NOT fixed in this release

- Constraint body names are not resolved
  ([issue #3](https://github.com/mycr0ft/sysmlpy/issues/3), finding 4).
  This is a significant semantic-analyzer feature, not a one-line fix;
  deferred to a follow-up release. Documented in STATUS.md and README.

## v0.44.0 (2026-08-26)

### :bug: Bug Fixes

- **`KeyError: 'item'` crash on `interface … connect … to …`
  usages ([issue #1](https://github.com/mycr0ft/sysmlpy/issues/1)).**
  `InterfaceBody.get_definition()` was emitting `"ownedRelatedElement"`
  but `InterfaceBody.__init__` was reading `"item"`. The visitor emits
  `"item"`, so fresh loads worked; the first re-parse of a model
  containing an interface-usage that named both ends raised
  `KeyError: 'item'`. `get_definition()` now emits `"item"` so the
  round-trip is consistent. Regression tests:
  `test_interface_connect_to_regression_gh1`,
  `test_interface_body_get_definition_roundtrip`.

### :arrow_up: Upstream / Grammar

- **Vendored ANTLR4 grammar updated from OMG 2026-03 to OMG 2026-05
  ([PR #2](https://github.com/mycr0ft/sysmlpy/pull/2) by
  [@HansBug](https://github.com/HansBug)).** Grammar source aligned
  with [daltskin/sysml-v2-grammar
  v2026.05.0](https://github.com/daltskin/sysml-v2-grammar); generated
  parser sources regenerated with ANTLR 4.13.2. Four production
  changes:
  - `annotatingMember` — now accepts an explicit `memberPrefix`
    visibility (SYSML21-319, SysML 2.1 RTF Ballot 1).
  - `payloadFeature` — `identification`-required alternatives and
    `ownedFeatureTyping` / `ownedMultiplicity` pair normalized
    (OMG 2026-05 KeBNF sync).
  - `framedConcernUsage` — second alternative switched from
    `calculationBody` / `calculationUsageDeclaration` to
    `requirementBody` / `constraintUsageDeclaration` (SYSML21-366).
  - `filterPackage` — dropped the stub alternative in favor of the
    official `filterPackageImportDeclaration` production.
  Local grammar patches (GUARD keyword, qualifiedIdentification,
  metadataAccessExpression, DOT bodyExpression, view-rendering
  keywords, required-visibility `importRule`) preserved.
  Visitor-downstream impact: **zero** changes to `antlr_visitor.py`
  or `grammar/classes.py`. Test results: 408/408 fast tests pass;
  118/123 conformance (5 pre-existing failures byte-identical to
  baseline).

## v0.43.0 (2026-08-26)

### :bug: Bug Fixes

- **Fixed `KeyError: 'item'` crash on `interface … connect … to …`
  usages ([issue #1](https://github.com/mycr0ft/sysmlpy/issues/1)).**
  `InterfaceBody.get_definition()` was emitting `"ownedRelatedElement"`
  but `InterfaceBody.__init__` was reading `"item"`. The visitor
  emits `"item"`, so fresh loads worked; the first re-parse of a
  model containing an interface-usage that named both ends raised
  `KeyError: 'item'`. `get_definition()` now emits `"item"` so the
  round-trip is consistent. Regression tests:
  `test_interface_connect_to_regression_gh1`,
  `test_interface_body_get_definition_roundtrip`.

## v0.42.0 (2026-08-26)

### :bug: Bug Fixes

- **`satisfy R : T by p;` crashed with NameError.** The satisfy /
  assert-constraint / requirement-constraint makers called
  `_build_feature_specialization_part(fsp_ctx)` — a function that was
  never defined. Any input with a featureSpecializationPart after the
  ownedReferenceSubsetting (e.g. `satisfy R : SomeType by p;`,
  `assert someConstraint : CType;`) raised `NameError` at parse time.
  All three sites now call `_build_full_specialization_from_fsp`
  (which handles all four specialization kinds), and the grammar-side
  `SatisfyRequirementUsage.fsp` consumption already supported the shape.

- **Chained re-declarations lost every segment after the first.**
  `attribute :> base.x;` emitted `subsettedFeature: ['base']` and an
  empty chain — the `.x` was dropped at both visitor and grammar layers:

  - Visitor: the six specialization-collection loops (subsettings /
    redefinitions / references x two builders) appended each
    QualifiedNameContext separately, losing dot relationships. New
    helpers (`_dotted_segments`, `_emit_owned_chain`,
    `_collect_owned_contexts`) emit one Owned* dict per source chain
    with head QualifiedName + OwnedFeatureChain for remaining segments.
  - Grammar classes: `OwnedSubsetting` / `OwnedRedefinition` kept the
    head *or* the chains (if/else). Both now keep both; dump joins all
    segments with '.'.
  - `Usage.redefined_name` resolves to the leaf segment (`x` for
    `:> base.x`) by walking head + chain in order.
  - Semantic analyzer: `_chain_segments` feeds reference collection so
    chained forms now report/resolve full dotted names —
    `attribute :> missing.chain;` yields
    `UNDEFINED_SYMBOL ... 'missing.chain'`, and feature-chain
    compatibility checks see `engine::name` again.

### :white_check_mark: Verification

- ``tests/redefined_name_test.py``: 14 / 14 passing — adds four cases:
  satisfy-with-typing no-crash, assert-constraint typing round-trip,
  chained-subset dump + leaf-name resolution, and chained-subset
  visibility to the semantic analyzer.
- Fast suite (9 files): 402 passing, zero regressions.
- Conformance: 118 / 123 — identical failure set to v0.41.0.

## v0.41.0 (2026-08-26)

### :sparkles: Improvements

- **Full-specialization capture across usage kinds.** v0.40.0 fixed
  `attributeUsage` only; every other usage maker still used the
  typed-by-only `_build_specialization(typed_by)` helper, dropping
  `:>`, `:>>`, and `::>` specializations for actions, calculations,
  constraints, requirements, use cases, interfaces, and nested
  occurrences.

  New `_full_specialization_for_ctx(ctx)` helper walks any usage-like
  ANTLR context (`ctx.usage()…`, `ctx.usageDeclaration()…`, or any
  `<x>UsageDeclaration()` holder) to its featureSpecializationPart and
  builds the full dict via `_build_full_specialization_from_fsp`.
  Twelve visitor sites now prefer it with the typed-by path kept as a
  defensive fallback: use-case, calculation, constraint, requirement,
  interface, analysis-case, assert/satisfy, objective-member,
  constraint-declaration, nested-occurrence, action-element, and the
  top-level usage-element dispatch.

- **API-level rendering.** `Action.load_from_grammar` now captures all
  four specialization kinds into `_typed_by_name` / `_specializes_names`
  / `_redefined_refs` / `_referenced_refs`, and the hand-rolled
  `dump()` methods on `Action`, `Interface`, `UseCase`, and
  `Requirement` render them:

      action a1 :> BaseType;
      action a2 ::> RefType;
      action a3 :>> RedefType;

  The `references` keyword form canonicalizes to the `::>` operator
  form (matching grammar-side dump behavior).

- **`Usage.redefined_name`** now walks deeper declaration nestings
  (e.g. ActionUsageDeclaration -> UsageDeclaration -> FeatureDeclaration)
  so it works on Action usages, not just Attribute.

### :white_check_mark: Verification

- ``tests/redefined_name_test.py``: 10 / 10 passing — adds API-level
  round-trip cases for actions covering all four kinds plus the
  ``redefined_name`` helper on Action.
- Fast suite (partial + redefined-name + grammar + class + main +
  navigate + repr + semantic + import): 410 passing, zero regressions.

## v0.40.0 (2026-08-26)

### :bug: Bug Fixes

- **`References` (``:>`` / `references` keyword) implemented in the grammar
  side.** Previously the `FeatureSpecialization` dispatch in
  `grammar/classes.py` had a silent ``print("References not yet
  implemented")`` stub for ``References`` relationship items, so any
  ``ref attribute ::> X;`` / ``ref attribute references X;`` form lost
  its specialization on round-trip (dump emitted ``attribute ;`` with
  no `::>` / `references` keyword). The visitor never emitted dicts
  for ``References`` either.

  Fix:
  - `grammar/classes.py`: new ``References`` class (mirrors
    ``Redefinitions`` but with ``::>`` / ``references`` keyword and
    ``OwnedReferenceSubsetting`` children). The
    ``FeatureSpecialization`` dispatch now routes ``References`` to it
    instead of printing.
  - `antlr_visitor.py`: ``References`` branch in both
    ``_build_full_specialization_from_ctx`` and
    ``_build_full_specialization_from_fsp`` (operator + keyword
    forms). The top-level ``attributeUsage`` path in
    ``_visit_usage_element_dict`` was the only one still using the
    typed-by-only ``_build_specialization`` helper; it now uses
    ``_build_full_specialization_from_ctx`` so the full specialization
    list (Typings + Subsettings + Redefinitions + References) is
    captured.

  ``redefined_name`` and ``display_name`` already handled
  ``References`` (via the ``referencedFeature`` fallback added in
  v0.39.0), so this release brings the loader in sync with the
  helpers — `ref attribute ::> MyType;` now round-trips and
  `attribute.redefined_name == "MyType"`.

### :white_check_mark: Verification

- ``tests/redefined_name_test.py``: 8 / 8 passing — adds two new
  cases for the operator and keyword forms of `References`.
- ``tests/grammar_test.py``: 97 / 97 passing (was 96) — adds
  ``test_attribute_ref_references_operator_roundtrip`` which
  exercises all four kinds (Typings, Subsettings, Redefinitions,
  References) in one model.
- partial + grammar + class + main + navigate + repr + semantic +
  import: 397 / 397 passing (zero regressions on the fast suite).
- Conformance: 118 / 123 — identical failure set to v0.39.0 (no
  regressions; the 5 pre-existing failures, including
  ``Import_Visibility_Valid`` whose XPECT expects a syntax error,
  are unchanged).

## v0.39.0 (2026-08-26)

### :bug: Bug Fixes

- **Redefined / subset / referenced Usage name now reachable from Python.**
  For ``attribute :>> exampleAttribute = "Example Value";`` and similar
  ``:>`` / ``::>`` re-declarations, the user-visible identifier lives
  only in the grammar's re-declaration chain — not on the feature
  ``identification``. ``Usage.load_from_grammar`` previously returned a
  UUID sentinel in that case (``attribute.name == "d68f2dc6-..."``
  while ``dump()`` correctly emitted ``exampleAttribute``). Two new
  helpers expose the resolved name without touching the historical
  ``self.name`` semantics:

  - ``Usage.redefined_name`` (property) — the last identifier segment
    of the first ``Redefinitions`` / ``Subsettings`` / ``References``
    chain in the feature specialization. Returns ``""`` when no
    re-declaration is present.
  - ``Usage.display_name`` (property) — user-meaningful name for the
    element. Identical to ``self.name`` when that field holds a real
    identifier; suppresses the auto-generated UUID sentinel so UI / log
    output stays clean.

  ``self.name`` is unchanged (still the UUID sentinel when no
  identification was given) so the symbol table, dump, navigation and
  semantic analyzer behavior is preserved.

  Motivating case (reported by a user):

      attribute :>> exampleAttribute = "Example Value";

  Before: ``attribute.name == "d68f2dc6-fa82-4828-8516-239b4aab1980"``.
  After: ``attribute.redefined_name == "exampleAttribute"`` (and
  ``attribute.display_name == "exampleAttribute"``).

### :white_check_mark: Verification

- ``tests/redefined_name_test.py``: 6 / 6 new tests passing — covers
  the original two-package model, subset/redefinition/display helpers,
  ``get_value()`` still works, dump still emits the right text.
- ``tests/partial_test.py`` + ``tests/grammar_test.py`` +
  ``tests/class_test.py`` + ``tests/main_test.py`` +
  ``tests/navigate_test.py`` + ``tests/semantic_test.py`` +
  ``tests/repr_test.py`` + ``tests/import_test.py``: 397 / 397 passing
  (zero regressions, including ``TestBasicUndefinedDetection::
  test_undefined_redefinition`` which exercises the same
  re-declaration-from-bare-name path).
- Conformance: 118 / 123 — identical failure set to v0.38.0 (no
  regressions; the 5 failures, including ``Import_Visibility_Valid``
  whose XPECT expects a syntax error, were pre-existing).

## v0.38.0 (2026-08-25)

### :sparkles: New Features

- **Partial-parse recovery.** New opt-in entry points surface whatever did
  parse when the input has syntax errors, instead of aborting with
  ``SysMLSyntaxError``:

  - ``PartialParseError`` (exception) carries ``.errors``,
    ``.partial`` (the visitor dict for the parsed part of the input),
    and ``.source``.
  - ``loads_partial(text)`` — same as ``loads`` but raises
    ``PartialParseError`` on errors; returns a clean dict on success.
  - ``load_partial(text)`` — same as ``load`` but raises
    ``PartialParseError`` with the partial visitor dict (still
    round-trippable through ``classtree`` + ``dump``) on errors.

  Motivating case: ``validation/valid/Import_Visibility_Valid.sysml``
  (its XPECT header expects a parse error on the visibility-less
  ``import ScalarValues;``, which the grammar legitimately rejects).
  Before: every loader in the test suite crashed on it. Now:
  ``loads_partial`` returns a dict with the three valid imports and the
  broken import dropped; ``load_partial`` gives you a Model whose
  ``Dump()`` produces:

      package ImportVisibility {
         public import ScalarValues;
         private import ScalarValues;
         protected import ScalarValues;
      }

  The strict ``loads`` / ``load`` are unchanged — they still raise
  ``SysMLSyntaxError`` on errors. ANTLR's default error-recovery
  strategy is used only when the partial entry point is called.

### :white_check_mark: Verification

- ``tests/partial_test.py``: 6/6 new tests passing.
- ``tests/grammar_test.py`` + ``tests/class_test.py`` +
  ``tests/main_test.py`` + ``tests/navigate_test.py`` +
  ``tests/semantic_test.py`` + ``tests/repr_test.py`` +
  ``tests/import_test.py``: 391/391 passing (zero regressions).
- Conformance: 118 / 123 — identical failure set to v0.37.0 (no
  regressions; the 5 failures, including ``Import_Visibility_Valid``
  whose XPECT expects a syntax error, were pre-existing). The
  conformance test uses the *strict* ``load_grammar`` path so its
  behavior is unchanged by this release.

## v0.37.0 (2026-08-25)

### :bug: Bug Fixes

Round-trip fixes found by benchmarking gosysml against the 123-file OMG
spec corpus (`tests/sysmlv2/`); Python now loads **122/123** corpus files
without exception (the one remaining failure, `Import_Visibility_Valid.sysml`,
has an XPECT header that *expects* a syntax error):

- **Implicit-package wrap could swallow its own closing brace.**
  `load_grammar` wraps non-`package` input in
  ``package __implicit__ { ... }`` by appending the closing brace to the raw
  source. When the source ended with a line comment and no trailing newline
  (e.g. `Subsetting_OwningType.sysml`), the brace landed on the comment line
  and was lexed away, producing `missing '}' at <EOF>`. The wrapped source is
  now newline-terminated before the brace is appended.

- **`AnnotatingElement` crashed on metadata / textual representations.**
  Only `Documentation` and `CommentSysML` were dispatched; a
  `MetadataFeature` or `TextualRepresentation` child set `children = None`
  and `dump()` raised `AttributeError`. Both now dispatch to their existing
  classes (which were present but unreachable) and unknown children dump as
  `""` instead of raising.

- **`BinaryInterfacePart.dump()` IndexError on malformed interface ends**
  (`InterfaceUsage_Invalid.sysml`). Now degrades gracefully for 0/1-end
  parts per the graceful-fallback contract.

- **Missing grammar classes for action-body successions.** The visitor has
  emitted `InitialNodeMember`, `ActionTargetSuccessionMember`, and
  `GuardedSuccessionMember` dicts since the control-flow work, but no
  matching grammar classes existed — any action body containing
  `first X;` / `then Y;` / `if c then X else Y;` raised
  `KeyError` at load time (broke `ActionTest.sysml`,
  `ControlNodeTest.sysml`, `DecisionTest.sysml`). Three new classes match
  the visitor dict shapes exactly, including `hasSemi` tracking so chained
  successions re-emit their own semicolons.

- **`TriggerExpression` lost WHEN triggers and crashed on empty ones.**
  The emitter only extracted `(AT|AFTER) argumentMember`; the
  `WHEN argumentExpressionMember` alternative was dropped and a missing
  argument member crashed with `TypeError: 'NoneType' object is not
  subscriptable`. `TimeTriggerKind` gained `isWhen`.

### :sparkles: Improvements

- `then merge m;` / `decide` / `join` / `fork` control nodes now carry
  their declared name through the visitor (`ControlNode.declaredName`)
  and dump it back.
- Guarded target successions (`if <cond> then X;`) and default targets
  (`else Y;`) round-trip inside action bodies.
- Nested `ref action a : A;` usages keep their `ref` prefix
  (`_make_action_usage_element` now extracts the occurrence prefix).
- `succession S first A1 if x==0 then A2;` round-trips including the
  succession name.
- `ActionBodyItem.dump()` appends the statement-terminating `;` for bare
  succession statements (skipped after `{...}` bodies or trailing doc
  comments).

### :white_check_mark: Verification

- `tests/grammar_test.py`: **96/96 passing** (includes full-model
  round-trips of ActionTest, ControlNodeTest, DecisionTest which now
  produce byte-identical strip_ws output).
- class/main/navigate/semantic/repr suites: all passing (268 tests).
- Conformance suite: 118 passed / 5 failed — identical failure set to the
  v0.36.3 baseline (no regressions).

## v0.36.3 (2026-08-20)

### :bug: Bug Fixes

- **View (and other prefixed-usage) body children are now exposed on the
  public API tree.** `Package.load_from_grammar` (in `definition.py`)
  built `View` objects for `ViewUsage` / `ViewDefinition` manually —
  setting `grammar` and `name` directly but never calling
  `load_from_grammar` — so `View.children` stayed empty and
  `view.attributes` (along with every other typed accessor) returned
  `[]` even when the body contained `attribute`, `part`, etc. The
  `ViewUsage` / `ViewDefinition` branches now call
  `View().load_from_grammar(...)` / `View(definition=True).load_from_grammar(...)`,
  matching how `Part` and the other occurrence usages are handled.

  Two supporting fixes in `usage.py` make prefixed usages fully
  round-trip:
  - `Usage.load_from_grammar` — the `declaration` branch (taken by
    prefixed usages such as `ViewUsage`, which carry their body directly
    on `grammar.body` — a `ViewBody` / `ViewDefinitionBody` — rather
    than nested under `grammar.usage.completion.body.body`) previously
    hardcoded `children = []`. It now extracts the body children with
    the same `DefinitionBodyItem → member → element` walk used by the
    usage path.
  - `Usage._ensure_body` — now handles grammars whose body lives
    directly on `grammar.body` (a body object with a `children` list),
    so `dump()` / re-serialization round-trips instead of raising
    `AttributeError: 'ViewUsage' object has no attribute 'usage'`.

  Regression tests added in `tests/navigate_test.py` (public-API
  accessor + `dump` content) and `tests/grammar_test.py` (full
  `load_grammar` → `classtree` → `dump()` round-trip).

## v0.36.2 (2026-08-18)

### :bug: Bug Fixes

- **`Requirement.load_from_grammar` now preserves short name, doc, and
  nested children in `dump()`.** Three gaps in the public `Requirement`
  class (in `usage.py`) were dropping data that the parser had correctly
  captured:
  - **Short name** (`requirement <'1'> R { … }`) — `declaredShortName`
    was read by the grammar layer but never propagated to
    `self.req_shortname`, so `dump()` emitted `requirement R;` with no
    `<'1'>`. Now extracted for both `RequirementUsage` and
    `RequirementDefinition`, with the `<>` wrappers stripped.
  - **Doc** (`doc /* … */`) — the body walk visited `DefinitionBodyItem`
    only to look for nested requirements; the `Documentation` /
    `CommentSysML` node inside `AnnotatingElement` was walked past and
    `self.doc` was never set. New `_extract_doc_from_body_item` helper
    walks `DefinitionBodyItem → DefinitionMember → DefinitionElement →
    AnnotatingElement → Documentation` and extracts the comment text via
    the new `_comment_body_to_text` module helper (strips `/* */` and
    ` * ` line prefixes).
  - **Nested children in `dump()`** — `dump()` built its body from
    `doc`/`subject`/`actors`/`req_attributes`/`req_constraints`/
    `assume_constraints` but never iterated `self.children`, so nested
    `requirement` usages were silently omitted from the output even
    though they were correctly stored on the parent. `dump()` now
    appends `child.dump()` for each child and indents multi-line body
    items (including multi-line doc blocks) so nested bodies render at
    the correct indentation level.

## v0.36.1 (2026-08-17)

### :sparkles: New Features

- **Nested requirement children.** `Requirement.load_from_grammar` now
  populates `self.children` with nested `requirement` usages and
  `requirement def` definitions encountered in the body. Previously the
  body walk stubbed out `DefinitionBodyItem` with `pass`, so nested
  requirements were parsed by the grammar but dropped from the public
  object tree. Deep nesting recurses correctly; `.parent` links are set
  on each child. Non-requirement nested elements (parts, items,
  attributes) are silently skipped for now. The grammar-object
  round-trip (`load_grammar` + `classtree`) is unaffected.

## v0.36.0 (2026-07-18)

### :sparkles: New Features

- **Boxes-backed state-machine visualizer.** New optional renderer
  `sysmlpy.boxes_view` produces a [`boxes`](https://github.com/mycr0ft/boxes)
  Diagram from a parsed SysML v2 `state def` — true rounded-corner
  `«state»` UML nodes, filled-circle initial pseudostate, bullseye final
  state, orthogonal port-to-port routing, and SVG / braille terminal
  output. This is an alternative to `as_state_transition_view()` (PlantUML),
  for the case where you want native UML shapes and don't want to round-trip
  through Java.
- Public API:
  - `sysmlpy.as_state_transition_view_boxes(model, focus=None)` → `boxes.Diagram`
  - `sysmlpy.render_state_transition_view(model, focus=None, routing=...)` → braille terminal string
  - `sysmlpy.render_state_transition_view_svg(model, focus=None, routing=..., scale=...)` → SVG string
  - All three are lazy-imported so `import sysmlpy` continues to work
    without `boxes` installed (raises `ImportError` with install hint on
    first call if `boxes` is missing).
- Adapter handles every state-machine construct that is actually in the
  SysML v2 language (per spec §7.18, `formal/26-03-02`, Sept 2025):
  - `entry;` / `entry action A;` / `do ...` / `exit ...` actions emitted
    as `entry / A`, `do / A`, `exit / A` attributes in the state box
  - Implicit initial pseudostate via `entry; then X;` succession
  - **`done` target** → `FinalState` bullseye node (one per region, reused)
  - **Guarded transitions** `transition T first A accept X if guard then B`
    → trigger and `[guard]` both appear in the edge label
  - **`accept X then Y;` shorthand** (`TargetTransitionUsage`) — extracts
    trigger and target, back-fills source from the most-recently declared
    state in the region
  - **Dotted feature-chain targets** like `S2.S3` — resolved through the
    full `OwnedFeatureChaining` chain, not just the last chaining name
  - **Nested composite states** — `state R1 { state a; state b;… }`
    parsed recursively; substates emitted as siblings with
    namespace-qualified names for now (visual nesting via `View.children`
    is a future boxes enhancement)
  - **`parallel` composite states** — when `isParallel=true` on the
    StateDefBody, the composite's «parallel» stereotype is emitted
    alongside «state»
- Re-exports the boxes pseudostate classes for diagram-author code that
  wants the state-machine vocabulary: `InitialPseudostate`,
  `JunctionPseudostate`, `ChoicePseudostate`, `ForkPseudostate`,
  `JoinPseudostate`, `FinalState`, `TerminatePseudostate`,
  `HistoryPseudostate`, `EntryPoint`, `ExitPoint`, `StateNode`.

### :bug: Fixes

- `grammar/classes.py:3909` — `DefaultInterfaceEnd.__init__` was calling
  `Usage(definition["usage"])` even when the visitor emitted an empty
  `usage: {}` dict (which happens for `perform … ;` lines inside an
  `interface … connect … { }` body). This crashed the entire parse with
  `AttributeError: This does not seem to be valid.` Fixed by switching
  the guard from `is not None` to truthy/non-empty. The official INCOSE
  SysML v2 Pilot `Flashlight Example.sysml` now loads successfully end-to-end.

### :books: Documentation

- New `docs/boxes_view.md` page covering the boxes-backed state-machine
  visualizer: install, API, supported constructs, the SysML v2 spec
  landscape (which pseudostates were deliberately dropped from UML 1.x),
  and a worked example with the OMG `StateTest.sysml` fixture.
- Updated `README.md` and `docs/PROJECT_SUMMARY.md` to mention the new
  visualizer and the boxes optional dependency.
- `STATUS.md` updated with the v0.36.0 capabilities and test counts.

### :white_check_mark: Tests

- New `tests/boxes_view_test.py` (19 tests): state-machine collection,
  composite states, `done` final-state, guard label, parallel flag,
  entry/do/exit attribute rendering, full-omg `StateTest.sysml` abridged
  extract, lazy attribute on `sysmlpy` namespace.
- Pre-existing `tests/plantuml_test.py` failures
  (`test_as_element_table_basic`, `test_as_state_transition_view_basic`)
  remain — they are unrelated to this work and predate it.

## v0.34.1 (2026-06-23)

### :bug: Fix standard library type resolution and add implicit import warnings

- `_is_resolved()` now checks unqualified (simple) names against the library symbol index, so bare references like `Real`, `String`, `Integer`, `Boolean` resolve without errors even without explicit imports.
- Added `LibrarySymbolIndex.get_simple_names()` with its own cache for efficient simple-name lookups.
- Added `_KNOWN_LIBRARY_SIMPLE_NAMES` hardcoded fallback derived from `_KNOWN_LIBRARY_SYMBOLS`.
- New `IMPLICIT_LIBRARY_IMPORT` warning emitted when a standard library type is used without an explicit import, suggesting the user add `import ScalarValues::<Type>;` or `import ScalarValues::*;`.
- `public import ScalarValues::*;` at package level propagates to child scopes and suppresses all warnings.
- All 118 semantic tests pass.

## v0.34.0 (2026-06-18)

### :exclamation: BREAKING: Remove deprecated SysML v1.x diagram functions

- Removed `as_block_definition_view()` — BDD is a SysML v1.x diagram; use `as_general_view()` in SysML v2.
- Removed `as_internal_block_diagram()` — IBD is a SysML v1.x diagram; use `as_interconnection_view()` in SysML v2.
- Removed `as_parametric_view()` — Parametric Diagram is a SysML v1.x diagram; use `as_action_flow_view()` in SysML v2.
- Removed `as_requirement_view()` — Requirement Diagram is a SysML v1.x diagram; use `as_general_view()` in SysML v2.
- Removed `as_package_diagram_view()` — Package Diagram is a SysML v1.x concept; use `as_package_view()` or `as_general_view()`.
- Removed orphan helpers: `_extract_constraint_parameters()`, `_extract_requirement_relationships()`, `_extract_connection_endpoints()`.

### :sparkles: New Features

- Added `as_browser_view()` — renders hierarchical model tree using PlantUML `@startwbs` (Work Breakdown Structure) syntax. Supports `focus`, `elements`, `style`, `custom_style`.
- Exported `as_browser_view` from `sysmlpy` package (`sysmlpy.as_browser_view()`).

### :white_check_mark: Tests

- Removed 34 tests covering removed v1 diagram functions.
- 120 plantuml tests pass (2 pre-existing unrelated failures remain).
- 350 core tests pass (class, main, repr, navigate, grammar, semantic).

## v0.33.6 (2026-06-15)

### :bug: Fix library import resolution with custom library paths

- Threaded `lib_roots` through `SymbolTable.build_from_model()` → `_resolve_imports()` → `_resolve_single_import()` → `_resolve_membership_import()` / `_resolve_namespace_import()`
- LibrarySymbolIndex fallback now passes custom library paths to `get_symbols()` instead of using only the default bundled library
- `import CustomTypes::*` now resolves correctly when `CustomTypes` is in a user-provided library path
- All 2 library project tests, 118 semantic tests passing

## v0.33.5 (2026-06-15)

### :bug: Fix bare `end` in interface def body — stop injecting spurious `part` keyword

- Removed `"PartUsage": "part"` from `DefaultInterfaceEnd` keyword mapping in `antlr_visitor.py:9269`
- `end e1 : Type;` now round-trips correctly as `end e1: Type;` (no extra `part`)
- `end item e1` / `end port e1` keywords preserved correctly
- 3 previously-failing interface round-trip grammar tests now pass
- All 95 grammar tests, 232 core tests, 118 semantic tests passing

## v0.33.4 (2026-06-15)

### :sparkles: Portion kind (timeslice/snapshot/individual) parsing, PlantUML rendering, interface keyword preservation

- Filled `portionUsage`/`individualUsage` visitor gaps in 4 nested dispatch paths
- Added `PortionUsage` grammar class with `dump()`/`get_definition()`, dispatch in `StructureUsageElement.__init__`
- Added `_make_portion_usage_prefix()` visitor helper for `PortionUsageContext`
- PlantUML `_get_stereotype()` includes `individual`/`timeslice`/`snapshot` prefixes
- Fixed `DefaultInterfaceEnd` keyword loss: visitor preserves `item`/`port` keywords in interface body ends
- Fixed `DefaultInterfaceEnd.__init__` for missing dict keys via `.get()`
- 4 new tests: portion round-trip (2), port kind stereotype (1), interface round-trip (1)

## v0.33.3 (2026-06-13)

### :sparkles: Grid view fix, sequence/case PlantUML views, guards documentation

- Fixed `_format_table_rows_plantuml` and `as_relationship_matrix_view`: replaced deprecated `salt` syntax with rectangle-based layout (PlantUML 1.2024.7+ compatible)
- Added `as_sequence_view()` — maps action flows/messages to PlantUML sequence diagram
- Added `as_case_view()` — maps parts/actions to PlantUML use-case diagram
- Created `docs/GUARDS.md` documenting canonical `if` keyword and transition ordering
- Added 6 regression tests for sequence/case views; updated 3 grid view tests

## v0.33.2 (2026-06-12)

### :bug: Fix PerformedActionUsage regression, accept double-quoted annotation strings

- Fixed `PerformedActionUsage.get_definition()` referencing `self.declaration` instead of `self.keyword`/`self.children` (Bug 1)
- Fixed `annotationDirective` visitor to accept `DOUBLE_STRING` (`"..."`) alongside `STRING` (`'...'`) (Bug 4)
- `_make_view_usage_dict` emits `ViewBody` directly for annotation body items

## v0.33.1 (2026-06-12)

### :bug: Fix guard keyword preservation in round-trip

- Fixed `GuardExpressionMember.get_definition()` to preserve `if` keyword
- Reorganized README.md changelog to chronological order

## v0.33.0 (2026-06-12)

### :sparkles: View/Rendering round-trip, qualified-name subject, guard keyword, render state directives

- Closed render/rendering round-trip gaps: `RenderingUsage` dispatch, `ViewRenderingMember`, `ViewRenderingUsage`, `ViewDefinitionBody`, `ViewBody`, `RenderStateMember` grammar classes
- Fixed 3 parser issues from `PARSING_ISSUES.md`:
  - Qualified-name `subject` (e.g., `subject a.b.c`)
  - `guard` as `if` alias
  - `render state` directives
- Removed author attribution `christophercox` → `mycr0ft` in 8 files

## v0.32.5 (2026-06-11)

### :bug: Fix double-space in redefinition and typing dump output

- Fixed `:>> ` (double space after `:>>`) when no specialization follows
- Fixed `: ` (double space after `:`) when no type name follows

## v0.32.0 (2026-06-11)

### :sparkles: Package imports exposed on public API

- Added `Package.imports` property — returns grammar objects for `Import` and
  `AliasMember` declarations within a package
- `Package.load_from_grammar()` now collects imports into a public-facing list
- `Package.add_import()` syncs with the new `._imports` list
- Imports now fully accessible in the public API while surviving round-trip
  (parse → dump → parse)
- 5 new tests in `TestPackageImportsProperty`


## v0.31.2 (2026-05-27)

### :memo: Update README version notes and LOC diagram

- Added v0.31.0 and v0.31.1 entries to README version history
- Regenerated `loc_history.svg` (89,715 LOC, 581 commits)

## v0.31.1 (2026-05-27)

### :bug: Fix pyproject.toml for CI compatibility

- Removed `allow_zero_version = true` from `[project]` table (invalid PEP 621 field)
- Removed duplicate `version` key in `[project]` (invalid per TOML spec)
- Fixed `authors` format for Poetry 2.1.x compatibility

## v0.31.0 (2026-05-27)

### :memo: Documentation Overhaul — Public API Showcase

All project documentation (`README.md`, `docs/quickstart.md`, `TUTORIAL.md`) has been
rewritten to showcase the modern public API, replacing all private underscore-prefixed
methods with their public equivalents.

**Changes across all docs:**
- `_set_child()` → `add_child()`
- `_set_name()` → `set_name()` / constructor `name=`
- `_set_typed_by()` → `set_typed_by()`
- `type=` parameter → `sysml_type=`
- `Model().load(text)` → `loads(text)`
- `load_grammar()` → `loads()`

**New sections added to README:**
- "Model Parsing" — `loads()` vs `parse()` with error handling
- "Model Navigation" — `find()`, `find_one()`, container protocol (`__iter__`, `__len__`,
  `__contains__`), `__str__`, typed property accessors (`model.parts`, `model.actions`),
  `sysml_type=` keyword with class support
- Semantic Analysis — `AnalysisResult.errors`/`.warnings`, `result.raise_on_errors()`,
  `bool(result)`, `strict=True`

**Grammar round-trip status updated:**
- All 77 tests pass (100%) — removed the outdated "16 deferred tests" caveat

**TUTORIAL.md:**
- `find_all()` examples replaced with `find()` / `find_one()` / `all()`
- "Convenience Functions" renamed to "Model Navigation" (v0.30.2+)
- `parse()` added to loading functions table
- Table of base classes updated with public method names

**docs/quickstart.md:**
- Full sweep from old private API (`_set_child`, `_set_name`, `_set_typed_by`)
  to public methods (`add_child`, constructor `name=`, `set_typed_by`)
- `Model().load(text)` pattern replaced with `loads(text)`
- Simplified imports (no more `classtree` in basic examples)

**AGENTS.md:**
- Updated grammar test status from "61 pass" to "77 pass (100%)"
- Removed "known expected failures" section
- Updated test commands to run specific file sets

### :white_check_mark: Test Results
- All core tests: 211/211 passing (class, main, repr, navigate, grammar, semantic)
- Grammar tests: 77/77 passing (100%)
- Semantic tests: 118/118 passing


## v0.30.2 (2026-05-27)

### :sparkles: Tier 3 — Polish

**Jupyter `_repr_html_()` for all model elements (`navigate.py`)**
- Added collapsible HTML tree representation: `model` in a Jupyter cell shows a
  nested `<details>` tree with type badges and element names, making interactive
  exploration much more pleasant.

**Non-raising `sysmlpy.parse()` variant (`__init__.py`)**
- Added `parse(text)` that returns `(Model, [])` on success and `(None, [errors])`
  on syntax error — never raises. Ideal for IDE integrations, linters, and batch
  processing pipelines.

**Stabilized mutation API — private methods made public (`usage.py`, `definition.py`)**
- `add_child(child)` — public alias for `_set_child()` (added in T2-1, now fully promoted)
- `set_name(name)` — public alias for `_set_name()`
- `set_typed_by(defn)` — public alias for `_set_typed_by()`
- `set_specializes(*parents)` — public alias for `_set_specializes()`
- `set_subsets(*parents)` — public alias for `_set_subsets()`
- `set_redefines(parent)` — public alias for `_set_redefines()`
- `get_child(path)` — public alias for `_get_child()`
- Old underscore-prefixed names kept for backward compatibility.

**Fixed `grammar = True` placeholder in `UseCase` and `Action` (`usage.py`)**
- Replaced `self.grammar = True` with `self.grammar = None` to avoid
  `AttributeError: 'bool' object has no attribute 'some_method'` in downstream code.

**Added return type annotations to all public functions**
- `loads()` → `Model`, `load()` → `Model`, `load_antlr()` → `Model`
- `Searchable.find()` → `list[Searchable]`, `Searchable.all()` → `list[Searchable]`
- `Usage.dump()` → `str`, `Package.dump()` → `str`, `Model.dump()` → `str`
- All `Usage` subclass `__init__` methods now have parameter type annotations.

**Documentation overhaul (`README.md`, `docs/quickstart.md`, `TUTORIAL.md`)**
- All docs updated to use public API: `add_child()` instead of `_set_child()`,
  `set_name()` instead of `_set_name()`, `set_typed_by()` instead of `_set_typed_by()`,
  `sysml_type=` instead of `type=`, etc.
- New "Model Parsing" section (README) with `parse()` example.
- New "Model Navigation" section (README) with `find()`, `find_one()`, container
  protocol (`__iter__`, `__len__`, `__contains__`), `__str__`, typed property
  accessors (`model.parts`, `model.actions`, etc.), and `sysml_type=` keyword.
- Semantic Analysis section updated to show `AnalysisResult.errors`/`.warnings`,
  `result.raise_on_errors()`, `bool(result)`, and `strict=True`.
- `TUTORIAL.md`: `find_all()` examples replaced with `find()` / `find_one()` / `all()`.
- `docs/quickstart.md`: full sweep from old private API to public methods.

### :white_check_mark: Test Results
- All core tests: passing
- Grammar tests: 77/77 passing (100%)
- Semantic tests: passing with new AnalysisResult/strict tests
- Navigate tests: passing with new find_one/container tests


## v0.30.1 (2026-05-27)

### :sparkles: Tier 1 — High Impact, Trivial Effort

**Exported `SysMLSyntaxError` from package root (`__init__.py`)**
- `from sysmlpy import SysMLSyntaxError` now works — no more reaching into
  `sysmlpy.antlr_parser` internals.

**Fixed stale `load()` and `load_antlr()` docstrings (`__init__.py`)**
- Both said "Returns: dict" but actually return `Model`. Fixed.
- Added proper return type annotations.

**Removed `print()` side effect on parse error (`__init__.py`)**
- Library code no longer prints to stdout when a `SysMLSyntaxError` is raised.
  The exception message already contains the full error text — the print was
  redundant and polluted CI pipelines.

**Added `find_one()` to `Searchable` mixin (`navigate.py`)**
- `model.find_one('Engine')` returns the element or `None` (never `IndexError`).
- Raises `LookupError` when multiple matches are found.

### :sparkles: Tier 2 — High Impact, Medium Effort

**Public `add_child()` method (`usage.py`, `definition.py`)**
- `parent.add_child(child)` appends child and sets `child.parent`.
- Returns `self` for fluent chaining: `pkg.add_child(Part(...)).add_child(Part(...))`
- Old `_set_child()` kept as backward-compatible alias.

**Container protocol — `__iter__`, `__len__`, `__contains__` (`navigate.py`)**
- `for child in model:` — iterate over direct children
- `len(model)` — number of direct children
- `'Engine' in model` — True/False by child name or identity

**`__str__` returns SysML text (`usage.py`, `definition.py`)**
- `str(part)` → `'part engine;'` instead of `"Part(name='engine')"`
- `repr(part)` still returns the constructor-mirroring form.

**`AnalysisResult` and `strict=True` (`semantic.py`)**
- `analyze()` now returns `AnalysisResult` (subclass of `list`, fully backward-compatible)
- `result.errors` — only error-severity issues
- `result.warnings` — only warning-severity issues
- `result.raise_on_errors()` — raises `ValueError` if errors exist
- `bool(result)` — `True` when no errors (warnings are OK)
- `analyze(model, strict=True)` — raises immediately on any error

**Renamed `type=` parameter to `sysml_type=` (`navigate.py`)**
- `model.find(sysml_type='part')` replaces `model.find(type='part')`
- Old `type=` keyword emits `DeprecationWarning` but still works
- `all(sysml_type=Part)` and `find_one(sysml_type='action')` also support the new name

### :white_check_mark: Test Results
- All core tests: passing
- Grammar tests: 77/77 passing (100%)
- New tests: `find_one()`, `add_child()` chaining, container protocol, `__str__` vs repr,
  `AnalysisResult`, `sysml_type=` deprecation — all passing


## v0.30.0 (2026-05-27)

### :sparkles: Constructor-Mirroring `__repr__` for All Public API Classes

Every public-facing class now has a `__repr__` that reads like a constructor call,
making debugging in REPLs and notebooks vastly more informative.

**Fixed `Usage.__repr__` (`usage.py`)**
- Replaced flawed `hasattr(self.grammar, 'definition')` heuristic with `self.is_definition`
  — 13 of 24 usage/definition classes (Action, State, Constraint, Requirement, UseCase,
  Calculation, Enumeration, View, Viewpoint, Concern, Case, AnalysisCase, VerificationCase)
  previously silently dropped `definition=True` from their repr.
- Added `_is_uuid()` helper — auto-generated UUID names are suppressed.
  `Part()` now prints `Part()` instead of `Part(name='f8a3...96b1')`.
- Added definition-path shortname lookup so `Part(definition=True, name='Engine', shortname='E')`
  works correctly for API-constructed objects.

**Fixed `Package.__repr__` (`definition.py`)**
- UUID names suppressed for `Package()` constructed without a name.

**Added `__repr__` to Store classes (`store.py`)**
- `InMemoryStore()` → `InMemoryStore(elements=0, edges=0)`
- `NetworkXStore(directed=True)` → `NetworkXStore(nodes=0, edges=0, directed=True)`
- `KuzuStore(database=':memory:')` → `KuzuStore(database=':memory:')`
- `CayleyStore(host='localhost', port=64210, label='sysmlpy')` → mirrors constructor

**Added `__repr__` to Semantic classes (`semantic.py`)**
- `SymbolTable()` → `SymbolTable(symbols=0, children=0)`
- `SemanticAnalyzer()` → `SemanticAnalyzer()`

### :white_check_mark: Tests

- Added `tests/repr_test.py` with **33 tests** covering all repr changes.

### :white_check_mark: Test Results

- repr tests: 33/33 passing
- All core tests: 200/200 passing (class, main, repr, semantic)
- Grammar tests: 77/77 passing (100%)


## v0.29.0 (2026-05-26)

### :tada: Complete Control Flow Node Support

**ALL 77 GRAMMAR TESTS PASSING (100%)**

All 14 control flow tests now passing:
- TerminateNode, SendNode (basic + via/to)
- ControlNode (merge, decision, fork, join)  
- IfNode (basic, else, elseif/else)
- WhileLoopNode (while, loop, with until)

### :white_check_mark: Test Results

- Grammar round-trip tests: 77/77 passing (100%)
- Control flow tests: 14/14 passing (100%)
- All tests: 140/140 passing (100%)


## v0.28.2 (2026-05-26)

### :sparkles: Control Flow Node Support (Partial)

- :sparkles: Added `TerminateNode` grammar class
  - Supports `terminate { action ...; }` syntax in action bodies
  - Follows same pattern as SendNode/AcceptNode classes
  - Fixes `test_Terminate_Node` (1 of 14 control flow tests)

- :bug: Fixed `ActionNodeUsageDeclaration.dump()` 
  - No longer outputs "action" keyword when declaration is None
  - Fixes `test_Send_Node` round-trip for `send msg { ... }` syntax
  - The "action" keyword is only output when there's an explicit declaration

### :white_check_mark: Test Results

- **Grammar round-trip tests:** 64/77 passing (83.1%)
- **Control flow tests:** 2/14 passing (TerminateNode, SendNode basic)
- **All non-control-flow tests:** 63/63 passing (100%)

### :memo: Known Remaining Issues

12 control flow tests still failing:
- SendNode with via/to (EmptyParameterMember structure)
- IfNode (3 tests) - condition expression handling
- WhileLoopNode (3 tests) - condition + until clause
- ControlNode (4 tests) - merge/decision/fork/join keywords
- ForLoopNode (1 test) - iteration syntax


## v0.28.1 (2026-05-26)

### :bug: PlantUML 1.2024.7+ Compatibility Fixes

- :bug: **as_element_table()** — Changed from `|=` table syntax to rectangle-based layout
  - Fixes "Syntax Error? (Assumed diagram type: sequence)" in generated images
  - All table rows now render as stacked rectangles

- :bug: **as_state_transition_view()** — Use `state` keyword instead of `rectangle`
  - Added initial state marker (`[*]`) pointing to first non-terminal state
  - Added final state markers (`--> [*]`) for terminal states (Error, Stopped, Final)
  - Fixes "syntax error (Assumed diagram type: state)" in generated images

- :bug: **as_internal_block_diagram()** — Removed `boundary { }` compartment syntax
  - PlantUML 1.2024.7+ removed support for compartment syntax in class diagrams
  - Ports now render as simple nested rectangles inside block
  - Fixes "syntax error (Assumed diagram type: class)" in generated images

- :bug: **Tabular Views** — Changed default output format from `"plantuml"` to `"markdown"`
  - `as_tabular_view()` — Default: `"markdown"`
  - `as_data_value_tabular_view()` — Default: `"markdown"`
  - `as_relationship_matrix_view()` — Default: `"markdown"`
  - PlantUML 1.2024.7+ removed support for legacy table syntax
  - Markdown and HTML formats work universally across all versions

- :bug: **Legend Tables** — Changed all 11 legend definitions from table format to plain text
  - Changed `|= Relationship |= Notation |` to `Relationship: Notation`
  - Ensures legends render in all PlantUML versions

### :wastebasket: Cleanup

- Removed 14 stale/duplicate PlantUML example files
- All 10 PNG examples referenced in README.md verified to render without errors

### :white_check_mark: Verification

All PlantUML examples render without errors:
- ✓ 03-vehicle-structure.png
- ✓ 06-interconnection.png
- ✓ 07-general-view.png
- ✓ 08-package-view.png
- ✓ 11-internal-block-diagram.png
- ✓ 13-action-flow-view.png
- ✓ 14-state-transition-view.png (now with start/end markers)
- ✓ 15-tree-diagram.png
- ✓ 16-element-table.png
- ✓ 17-textual-notation.png


## v0.28.0 (2026-05-26)

### :sparkles:

- :sparkles: Gap 10 Complete — Missing Grammar Classes
  Added `TextualRepresentation`, `MetadataFeature`, `MetadataFeatureDeclaration`, and
  `OccurrenceUsageBody` grammar classes with full `dump()` and `get_definition()` support.
  Updated ANTLR visitor to dispatch textual representation and metadata feature annotations.

- :sparkles: Gap 11 Complete — Expression Resilience
  Replaced final `return NotImplementedError` in `InterfaceEnd.__init__` with graceful warning
  print. All expression operators now handle edge cases without raising exceptions.

- :sparkles: Package Diagram View (`as_package_diagram_view`)
  Complete implementation of SysML v2 Package diagrams. Shows package hierarchy with elements
  nested inside their containing packages (folder-style rendering). Supports `focus`, `style`
  (bw/color), `direction`, `include_legend`, `show_element_types`, and handles deeply nested
  packages. Added 7 tests in `tests/plantuml_test.py`.

- :sparkles: Parametric Diagram View (`as_parametric_view`)
  Complete implementation of SysML v2 Parametric diagrams. Shows constraint definitions with
  parameter compartments (including types like `Real`), supports nested package traversal,
  focus element, style options (bw/color), and legend. Added 7 tests in `tests/plantuml_test.py`.

- :sparkles: Internal Block Diagram View (`as_internal_block_diagram`)
  Complete implementation of SysML v2 Internal Block Diagrams. Shows block boundary with ports,
  nested parts, flow connections with source/target arrows, and connection usage with blue connector
  arrows. Supports `focus`, `style` (bw/color), `direction`, `show_parts`, `show_ports`, 
  `show_connections`, and custom styling. Added 6 tests in `tests/plantuml_test.py`.

- :sparkles: Block Definition Diagram View (`as_block_definition_view`)
  Complete implementation of SysML v2 Block Definition Diagrams. Shows block definitions with
  compartments for attributes, ports, and part references. Displays generalization relationships.
  Added 8 tests in `tests/plantuml_test.py`.

- :sparkles: Send/Accept Action Usage Handling (Gap 6)
  Full implementation of send/accept actions in action bodies. Added grammar classes
  `SendNode`, `AcceptNode`, `IfNode`, `WhileLoopNode`, `ForLoopNode`, `ControlNode` and
  corresponding declaration classes. Visitor extracts signal/event names and creates nested
  Action children (e.g., `send_MySignal`, `accept_TriggerEvent`).

- :sparkles: Library Import Loading (Gap 8)
  Implemented library loading mechanism in `antlr_parser.parse()`. When `library` parameter
  is provided, all `.sysml` and `.kerml` files from library directories are loaded and
  prepended to content before parsing. Enables standard library definitions for import
  resolution.

- :sparkles: Code Deduplication (Gap 5)
  Created `_extract_name_from_ident()` helper function and refactored 7+ locations in
  `antlr_visitor.py`. Reduced code duplication by ~150 lines.

### :bug:

- :bug: Fixed `PackageBody.dump()` format - consistent brace formatting
- :bug: Fixed `RootNamespace.get_definition()` - clarified SysML vs KerML handling
- :bug: Fixed `InterfaceEnd.__init__` - replaced `return NotImplementedError` with warning print

### :white_check_mark:

- :white_check_mark: All 144 PlantUML tests passing
- :white_check_mark: All 190 tests passing (class, main, plantuml)
- :white_check_mark: 61 / 77 grammar round-trip tests pass (16 deferred control-flow)

### :memo:

- :memo: Updated `TODO-gaps.md` - Gap 4, 10, 11 now 100% complete
- :memo: Zero TODOs remaining in codebase

---


## v0.27.2 (2026-05-25)

### :sparkles:

- :sparkles: Requirement View (`as_requirement_view`)
  Renders requirement diagrams with stereotypes (`<<requirement>>`, `<<requirement def>>`),
  documentation notes, attributes, and constraints. Supports satisfy/verify/derive/refine
  relationship extraction. Includes all standard view parameters: `focus`, `elements`,
  `style` (bw/color), `direction`, `max_depth`, `show_external`, and custom styling.
  Added 8 tests.

- :sparkles: Interface/UseCase/Message name extraction + visitor support
  Added `load_from_grammar()` methods to `Interface`, `UseCase`, and `Message` classes.
  Added `_make_use_case_usage_dict()` and `_make_message_dict()` to antlr_visitor.py.
  Fixed `Interface.connections` attribute conflict with Searchable mixin property.
  UseCase and Message now parse correctly from SysML text.

### :white_check_mark:

- :white_check_mark: All 116 PlantUML tests passing
- :white_check_mark: All 60 class/main tests passing
- :white_check_mark: 61 / 77 grammar round-trip tests pass (16 deferred control-flow)

### :memo:

- :memo: Updated `TODO-gaps.md` with completion status for Requirement View and
  Interface/UseCase/Message visitor support.

---


## v0.27.0 (2026-05-25)

### :sparkles:

- :sparkles: General View (`as_general_view`)
  Renders all SysML v2 element types (packages, parts, items, ports, actions,
  states, connections, flows, requirements, constraints, calculations, etc.)
  with stereotype-based styling. Supports `focus`, `elements`, `max_depth`,
  `show_external`, `auto_include_connections`, `direction`, B&W/color toggle,
  and legend.

- :sparkles: Package View (`as_package_view`)
  Renders package structure with contained definitions, usages, and
  cross-package import/dependency arrows. Supports filtering by focus package
  and depth control.

- :sparkles: Tabular View (`as_tabular_view`)
  GridView specialization that renders model elements as a table.
  Supports PlantUML, Markdown, and HTML output formats.
  Columns are configurable; defaults to name, type, and description.

- :sparkles: Data Value Tabular View (`as_data_value_tabular_view`)
  GridView specialization focused on attribute values.
  Renders attributes with name, type, value, and units columns.
  Supports PlantUML, Markdown, and HTML output.

- :sparkles: Relationship Matrix View (`as_relationship_matrix_view`)
  GridView specialization that renders a matrix of relationships between
  two sets of elements. Supports PlantUML, Markdown, and HTML output.

- :sparkles: Grammar resilience — 68+ `NotImplementedError` → graceful handling
  Every `raise NotImplementedError` in `grammar/classes.py` has been replaced
  with either real field storage + `dump()`/`get_definition()` support, or a
  warning print that silently skips the unrecognized element. The parser no
  longer crashes on edge cases.
  Key stubs fully implemented: `PortionKind`, `PrefixMetadataMember`,
  `LifeClassMembership`. Missing classes added: `DefinitionBody`,
  `DefinitionBodyItem`, `FeatureSpecializationPart`, `SubclassificationPart`.

### :white_check_mark:

- :white_check_mark: 108 PlantUML tests passing (up from 101 in v0.26.0)
- :white_check_mark: 61 / 77 grammar round-trip tests pass
  (16 deferred: action control-flow node classes not yet ported)
- :white_check_mark: All 123 OMG XPect conformance tests pass (100%)

### :memo:

- :memo: Updated README.md, STATUS.md, and docs/PROJECT_SUMMARY.md for v0.27.0
- :memo: Added AGENTS.md — guidance for AI coding agents working on sysmlpy


## v0.19.0 (2026-05-22)

### :sparkles:

- :sparkles: Semantic analysis engine with undefined symbol detection
  New `analyze()` function walks the parsed model tree, builds a
  hierarchical symbol table, and cross-references all type, subsetting,
  and redefinition references against defined symbols.

- :sparkles: Import resolution
  Resolves `import Package::*` (namespace), `import Package::Element`
  (membership), and `import Package::*::**` (recursive) imports.
  Imported symbols become visible in the importing scope.

- :sparkles: SymbolTable with hierarchical scope resolution
  Each package and definition creates a child scope. References resolve
  through parent scopes. Qualified names like `P::A` and
  `Outer::Inner::DeepPart` resolve correctly across arbitrary depth.

- :sparkles: 80+ standard library symbols whitelisted
  ScalarValues, ISQ quantities, and base KerML/SysML types are
  pre-recognized so they don't trigger false positives.

### :white_check_mark:

- :white_check_mark: 530 tests passing (43 semantic tests, 6 new import tests)
- :white_check_mark: SemanticIssue dataclass with severity, code, message, element, reference

### :memo:

- :memo: Updated README.md with Semantic Analysis section, import resolution
  documentation, and symbol resolution capabilities.


## v0.17.1 (2026-05-21)

### :sparkles:

- :sparkles: CayleyStore — graph database backend via HTTP API
  Supports BoltDB, LevelDB, and in-memory Cayley backends.
  Stores elements as quads (subject, predicate, object, label).
  Provides namespace isolation via labels for multi-tenant scenarios.
  Full Store protocol implementation: put, get, delete, children,
  parents, relationships, query, has, ids, clear, plus graph
  traversal (descendants, ancestors, path), connected components,
  cycle detection, centrality, subgraph extraction, and GraphML export.

### :bug:

- :bug: NetworkXStore.put() now adds the node before adding edges
  Previously, put() only created edges when parent_id was provided,
  but never stored the node data itself. This caused get() to return
  None, delete() to return False, query() to find nothing, and all
  graph operations to fail silently.

- :bug: Usage.__init__() now initializes completion to UsageCompletion()
  Previously, programmatic API created Usage with completion=None while
  the parser always created a UsageCompletion. This caused set_value()
  to crash with AttributeError and dump() to omit the semicolon,
  breaking round-trip consistency for Item, Part, Port, and Attribute.

### :white_check_mark:

- :white_check_mark: 100% test suite pass rate (487/487)
  All 56 grammar round-trip tests pass.
  All 123 OMG XPect conformance tests pass.
  All 82 store tests pass (including NetworkX).
  All 53 class tests pass (programmatic API).
  All 16 import tests pass.

### :memo:

- :memo: Updated README.md with v0.17.0 release notes, CayleyStore
  documentation, storage backend comparison table, and Docker examples.
- :memo: Updated docs/index.md and docs/quickstart.md with Cayley
  storage backend documentation.


## v0.16.0 (2026-05-21)

### :sparkles:

- :sparkles: 100% grammar round-trip test coverage (56/56)
  Added support for analysis case usage with subject/objective members,
  trade study analysis examples, calculation redefinition (`calc :>> name`),
  case body items (subjectMember, objectiveMember, actionBodyItem,
  returnParameterMember), and nested calculation usages within analysis bodies.

### :bug:

- :bug: ImportPrefix now allows imports without explicit visibility
  Per SysML v2 spec, imports without a visibility keyword default to
  private. Previously raised ValueError requiring explicit visibility.

### :white_check_mark:

- :white_check_mark: Grammar round-trip tests: 34/56 → 56/56 passing
- :white_check_mark: Import visibility tests updated to reflect correct behavior

### :memo:

- :memo: Updated README.md with v0.16.0 release notes


## v0.1.0 (2026-05-17)

### :ambulance:

- :ambulance: Added configuration to workflow
  ([`e8b932b`](https://github.com/mycr0ft/sysmlpy/commit/e8b932b9ab4e3e16ff43cf4549c571e70a5cd218))

- :ambulance: Correct workflow yaml
  ([`8c410ee`](https://github.com/mycr0ft/sysmlpy/commit/8c410ee7e486b7624e31d19faf94c6692b110f88))

- :ambulance: Fix for attribute change when adding units
  ([`1daacac`](https://github.com/mycr0ft/sysmlpy/commit/1daacac3e81062bd35a5cac832f3cafccc9317a9))

- :ambulance: Fix for build script
  ([`4c6f238`](https://github.com/mycr0ft/sysmlpy/commit/4c6f238afcf37c8620f082dfee19a8a4282a47e3))

- :ambulance: Fix to upload to pypi
  ([`3309eb5`](https://github.com/mycr0ft/sysmlpy/commit/3309eb5641f3671e6690bd61ac04b986c5d0a0c8))

- :ambulance: Fixed critical grammar changes with SysML and KerML overwrites.
  ([`34978bb`](https://github.com/mycr0ft/sysmlpy/commit/34978bbd33a0793cb618605aa87950fda64d5f68))

- :ambulance: Fixing merge errors from black
  ([`e101e70`](https://github.com/mycr0ft/sysmlpy/commit/e101e70ea50ccd52cc5226c6860bcbe1b9411d3a))

- :ambulance: Permissions fix
  ([`8c5ea13`](https://github.com/mycr0ft/sysmlpy/commit/8c5ea13b9d28aa2f846fc9f1e7f985eeae7e615d))

### :bug:

- :bug: Added test and definition file that was causing the error.
  ([`b7787d4`](https://github.com/mycr0ft/sysmlpy/commit/b7787d4ccba53e421e3f877a46eca331698e2950))

- :bug: Adding textx to requirements.
  ([`d3c1c76`](https://github.com/mycr0ft/sysmlpy/commit/d3c1c767b39a68d67c0eea7802982de770c1bc48))

- :bug: Commiting all prior changes.
  ([`db0be56`](https://github.com/mycr0ft/sysmlpy/commit/db0be5652f83e9ea55052292914465c75616cc48))

- :bug: Duplicate feature chaining in primary expression.
  ([`8217463`](https://github.com/mycr0ft/sysmlpy/commit/821746349450467c3ab9b46bc86922d2476f8640))

- :bug: Enforce some syntax with Models always starting with packages.
  ([`0cccdf1`](https://github.com/mycr0ft/sysmlpy/commit/0cccdf1d5f97c864d82edffc9ec54bd93cf1cb54))

- :bug: Fix for definition naming.
  ([`ff62dc1`](https://github.com/mycr0ft/sysmlpy/commit/ff62dc10131d8c53fd4361f7100403dc1c4424f6))

- :bug: Fix poetry build for pypi builds.
  ([`3c90e28`](https://github.com/mycr0ft/sysmlpy/commit/3c90e28707710002018569509f87e9266ccef446))

- :bug: Fixed an issue where something defined within a package could not be typed by another
  definition
  ([`ee257eb`](https://github.com/mycr0ft/sysmlpy/commit/ee257eba9cdaec2a8ac52f65cf702881879aa445))

- :bug: Fixed changes to primary expression in attribute
  ([`ace773c`](https://github.com/mycr0ft/sysmlpy/commit/ace773c595db76e208fe4d909f91ceae4171fef6))

- :bug: Fixed issue with port subnodes.
  ([`67720b1`](https://github.com/mycr0ft/sysmlpy/commit/67720b19307df138dff10d5138f74aba1fa87734))

- :bug: Fixed issue with Primary expression get definition response.
  ([`5512466`](https://github.com/mycr0ft/sysmlpy/commit/55124661dd6f8c08efb2136db65bb22111012ae4))

- :bug: Fixed issue with usage classes with body objects.
  ([`afc5522`](https://github.com/mycr0ft/sysmlpy/commit/afc5522c64088595030f68d578af2f303613226e))

- :bug: Fixes for load_grammar functions.
  ([`0e45818`](https://github.com/mycr0ft/sysmlpy/commit/0e4581889f55928576e939026a8ab5c3debdccc0))

- :bug: Removing optional from in flow statement that won't return programmatically.
  ([`716961b`](https://github.com/mycr0ft/sysmlpy/commit/716961b003e51c286af8c63e2cad5d5806acef20))

- :bug: Reverting change to author.
  ([`ae5d19e`](https://github.com/mycr0ft/sysmlpy/commit/ae5d19e5581b3493e985bd01bb356b1dcd3d1618))

- :bug: Updated secondary primary expression in attribute.
  ([`97f2086`](https://github.com/mycr0ft/sysmlpy/commit/97f20867c29b577ce0f3d6d3eb5dd1cabe0dafaf))

- :bug: Workflow fixes
  ([`9b883ea`](https://github.com/mycr0ft/sysmlpy/commit/9b883eaef9932e80299dc94ede0646a2ceb1a405))

### :chart_with_upwards_trend:

- :chart_with_upwards_trend: Add lines of code history plot
  ([`4b86c9c`](https://github.com/mycr0ft/sysmlpy/commit/4b86c9cdbf6e5e202f1ba2db30a0724453e39013))

### :construction:

- :construction: Adding more documentation and cleanup
  ([`8a8675e`](https://github.com/mycr0ft/sysmlpy/commit/8a8675e3828beef65903491a578477e14ba5ffa5))

- :construction: Fix yaml
  ([`0fc1c2f`](https://github.com/mycr0ft/sysmlpy/commit/0fc1c2f860cfc3a5e61138c53cfc5b4b8a24ab84))

- :construction: Fixes and updates to CI/CD
  ([`c0640f1`](https://github.com/mycr0ft/sysmlpy/commit/c0640f1ded084d7d178d0a1a0ad87e434c388d37))

- :construction: Forgot to git pull
  ([`4cf3100`](https://github.com/mycr0ft/sysmlpy/commit/4cf3100b719f9ee17beb556b116cf46fd9db1886))

- :construction: More adds.
  ([`42258b6`](https://github.com/mycr0ft/sysmlpy/commit/42258b66704bb42a2f2b2632722bab30887cb8a9))

### :heavy_plus_sign:

- :heavy_plus_sign: Adding pytest-html to test workflow.
  ([`4f2cedc`](https://github.com/mycr0ft/sysmlpy/commit/4f2cedc50162ac2013b5dc60481a7bc646debad3))

- :heavy_plus_sign: Using poetry package management, added dependencies.
  ([`5c625dd`](https://github.com/mycr0ft/sysmlpy/commit/5c625dd6e51a6090a699aab229c335d8946d7bd5))

### :lock:

- :lock: Switch PyPI publishing to Trusted Publishing (OIDC)
  ([`64b6325`](https://github.com/mycr0ft/sysmlpy/commit/64b6325d320cda4ae3790abd087a572b9e7cfadd))

- Remove PYPI_API_TOKEN dependency — uses GitHub OIDC instead - Add id-token: write permission for
  OIDC token minting - Update actions to v4/v5/v9 latest versions - Clean up codecoverage job Python
  version - Remove repository_password from semantic-release step

### :memo:

- :memo: Add LOC history plot to README
  ([`4582c59`](https://github.com/mycr0ft/sysmlpy/commit/4582c5989a9cf9dba9b0bb47fe98e0f4b0c59e96))

- :memo: Add optional dependencies to README, bump version to v0.12.0
  ([`9fbf40a`](https://github.com/mycr0ft/sysmlpy/commit/9fbf40a8baa68eb54fbdb2eedcd2fa2ebbd44e64))

- :memo: Added full docstrings to init
  ([`0e06f1d`](https://github.com/mycr0ft/sysmlpy/commit/0e06f1d73b476706eae4dddf02ff3e3b3c052ada))

- :memo: Added trello to Readme
  ([`26e304c`](https://github.com/mycr0ft/sysmlpy/commit/26e304c10ea7599259d75f43992996887161183a))

- :memo: Adding more badges.
  ([`76899b1`](https://github.com/mycr0ft/sysmlpy/commit/76899b192545087066493c7a65c388266c09d01c))

- :memo: Docstring coverage add to README
  ([`3720f3a`](https://github.com/mycr0ft/sysmlpy/commit/3720f3a07002b1129b90d552f7a291c8662c6c09))

- :memo: Documentation changes.
  ([`edfd629`](https://github.com/mycr0ft/sysmlpy/commit/edfd629ec5ef6611d2b9643706cee6b1bf40ea47))

- :memo: Fixes for README that were out of date.
  ([`e57a964`](https://github.com/mycr0ft/sysmlpy/commit/e57a964e6edcfb16b9f1b32128ef09c4ad670490))

- :memo: Fixing spacing.
  ([`25e78d0`](https://github.com/mycr0ft/sysmlpy/commit/25e78d01066b96146be587988e1735367747f52c))

- :memo: remove excess brackets
  ([`e258d1c`](https://github.com/mycr0ft/sysmlpy/commit/e258d1cdccbf3614b6be37f6322ddee006756809))

- :memo: Time to add documentationgit add docsgit add docs
  ([`f933521`](https://github.com/mycr0ft/sysmlpy/commit/f9335216ae484aa2145fd2178b206bcff510958b))

- :memo: Updates to project info to assist sphinx build.
  ([`939d2ff`](https://github.com/mycr0ft/sysmlpy/commit/939d2ff4867ccc792b78c8a1229ef937653093ec))

- :memo: Updates to readme, also added a loadfromgrammar function to Usage.
  ([`e999436`](https://github.com/mycr0ft/sysmlpy/commit/e999436193ccee31dfadaf5a193705cf61e99496))

- :memo: Updates to version
  ([`208cdd6`](https://github.com/mycr0ft/sysmlpy/commit/208cdd62db514b466b0b64aa70134e54cea46ce0))

### :robot:

- :robot: Add coverage badge
  ([`413323d`](https://github.com/mycr0ft/sysmlpy/commit/413323d7acea6f5898befcce5445b46790a461ea))

- :robot: Add coverage badge
  ([`199fa49`](https://github.com/mycr0ft/sysmlpy/commit/199fa497bb06bc68ac897f2031d951ae55ce1f9e))

- :robot: Add coverage badge
  ([`55e4a86`](https://github.com/mycr0ft/sysmlpy/commit/55e4a8612271bab3d213667538874e2c6ba84e5e))

- :robot: Format code with black
  ([`5d6c2b7`](https://github.com/mycr0ft/sysmlpy/commit/5d6c2b7ebf32d64c06b94bc1db719967f2839775))

- :robot: Format code with black
  ([`698816d`](https://github.com/mycr0ft/sysmlpy/commit/698816d7aa369c83e5b2484bb9cc7cffe4b64383))

- :robot: Format code with black
  ([`31bde37`](https://github.com/mycr0ft/sysmlpy/commit/31bde373a1d400f43c0d57a9e34bd0355e85c70e))

- :robot: Format code with black
  ([`02c18a9`](https://github.com/mycr0ft/sysmlpy/commit/02c18a93bc5d17ae7faa33f36ce7ac87c540e3fe))

- :robot: Format code with black
  ([`dc47ac1`](https://github.com/mycr0ft/sysmlpy/commit/dc47ac1fb0f93bb5eafee6a5bfafa094fd277a1b))

- :robot: Format code with black
  ([`6a9e45b`](https://github.com/mycr0ft/sysmlpy/commit/6a9e45be53f6588c7b217fe4c7e8e25f338eed0b))

- :robot: Format code with black
  ([`854bc64`](https://github.com/mycr0ft/sysmlpy/commit/854bc647fe7cec03abf05930a6b9ca5755b8b1c4))

- :robot: Format code with black
  ([`c848b0d`](https://github.com/mycr0ft/sysmlpy/commit/c848b0df54de5f50f594a0fff2d9a8bf96214340))

- :robot: Format code with black
  ([`52ddedd`](https://github.com/mycr0ft/sysmlpy/commit/52ddedd2d12f2add66196f3b2772886343515f55))

- :robot: Format code with black
  ([`cc74fa0`](https://github.com/mycr0ft/sysmlpy/commit/cc74fa09521b61f5d63c9310425fd75b5205f350))

- :robot: Format code with black
  ([`99b33a3`](https://github.com/mycr0ft/sysmlpy/commit/99b33a3a99a1a7f375f93872e512a2f788b767a3))

- :robot: Format code with black
  ([`81be427`](https://github.com/mycr0ft/sysmlpy/commit/81be42734aa4ee1cb09aeef3f3db9dbd6905d2f9))

- :robot: Format code with black
  ([`9f8a1d7`](https://github.com/mycr0ft/sysmlpy/commit/9f8a1d7777e63109fbee0e801c6ae688259b5303))

- :robot: Format code with black
  ([`904332e`](https://github.com/mycr0ft/sysmlpy/commit/904332e059a3790e990ed80368b2024efa21ab93))

- :robot: Format code with black
  ([`683bf47`](https://github.com/mycr0ft/sysmlpy/commit/683bf47c63626a2fe481e09a86cb0f172c11752a))

- :robot: Format code with black
  ([`c96819b`](https://github.com/mycr0ft/sysmlpy/commit/c96819be25bdcdf83277a10520d4f687c9e9a511))

- :robot: Format code with black
  ([`c8eb269`](https://github.com/mycr0ft/sysmlpy/commit/c8eb269bbdcd42c412e4f1bead30a538cb6c28c5))

- :robot: Format code with black
  ([`9af94da`](https://github.com/mycr0ft/sysmlpy/commit/9af94da1a4d5cd2e84faf37e0f51960267735b8f))

- :robot: Format code with black
  ([`37d9c36`](https://github.com/mycr0ft/sysmlpy/commit/37d9c36454eddfbf7671d781fb75ed7b7d3b7724))

- :robot: Format code with black
  ([`320a6a9`](https://github.com/mycr0ft/sysmlpy/commit/320a6a9362fa9b29fd3f6fe5853ac68f7be95606))

- :robot: Format code with black
  ([`22b38bd`](https://github.com/mycr0ft/sysmlpy/commit/22b38bd230918c03373f00d271fd19a1897f6402))

- :robot: Format code with black
  ([`aeaf778`](https://github.com/mycr0ft/sysmlpy/commit/aeaf778bdaf0ce957bed1c9107e5fc0dd61a7e27))

- :robot: Format code with black
  ([`7a24a97`](https://github.com/mycr0ft/sysmlpy/commit/7a24a971832e77d115eff763b1cdbd8657773e57))

- :robot: Format code with black
  ([`fd62a35`](https://github.com/mycr0ft/sysmlpy/commit/fd62a35a42224ebf52ae59021e386af4aa6f550f))

- :robot: Format code with black
  ([`e38b669`](https://github.com/mycr0ft/sysmlpy/commit/e38b6692ab78adb84027227ee45890f3c3f5724a))

- :robot: Format code with black
  ([`0449f57`](https://github.com/mycr0ft/sysmlpy/commit/0449f575e3311bcdcedf13a5717e59d321bab9ab))

- :robot: Format code with black
  ([`df738a0`](https://github.com/mycr0ft/sysmlpy/commit/df738a0c4229d5e94cca238ecaf5ff9f4f1063d2))

- :robot: Format code with black
  ([`cba4687`](https://github.com/mycr0ft/sysmlpy/commit/cba4687d7d923747583c7bc3eb612aaa15aec0ea))

- :robot: Format code with black
  ([`c3d3a59`](https://github.com/mycr0ft/sysmlpy/commit/c3d3a59419bf5179df2db61ccddbf0ec954a924c))

- :robot: Format code with black
  ([`30efad4`](https://github.com/mycr0ft/sysmlpy/commit/30efad483d9c1d1e847900ac24557fca547c62ba))

- :robot: Format code with black
  ([`2009f90`](https://github.com/mycr0ft/sysmlpy/commit/2009f90b6de416cc0587e87b6fef201232f31b74))

- :robot: Format code with black
  ([`a5d91c6`](https://github.com/mycr0ft/sysmlpy/commit/a5d91c6c3deb440e595766e43b99310980799f00))

- :robot: Format code with black
  ([`66a1f15`](https://github.com/mycr0ft/sysmlpy/commit/66a1f15fe8a2a84fdf0a612bd06a6b1b01301de4))

- :robot: Format code with black
  ([`9e4b07b`](https://github.com/mycr0ft/sysmlpy/commit/9e4b07b9dc622494bddfccca731c5e3697d0e451))

- :robot: Format code with black
  ([`5eac5cd`](https://github.com/mycr0ft/sysmlpy/commit/5eac5cd7818f7b0c2c253cc39a2d70794ad2a197))

- :robot: Format code with black
  ([`b609c87`](https://github.com/mycr0ft/sysmlpy/commit/b609c874afba53056b93e1b4cb91081ec7ad96bf))

- :robot: Format code with black
  ([`232a31e`](https://github.com/mycr0ft/sysmlpy/commit/232a31ee56899a0a25165f77db847960e0b78d9f))

- :robot: Format code with black
  ([`e8fe82b`](https://github.com/mycr0ft/sysmlpy/commit/e8fe82b892878e81cf8039e0e688751ebca09171))

- :robot: Format code with black
  ([`1d68ffc`](https://github.com/mycr0ft/sysmlpy/commit/1d68ffc665422100e5617e2a8fb6c6ced67b5cbf))

- :robot: Format code with black
  ([`a2a8e6e`](https://github.com/mycr0ft/sysmlpy/commit/a2a8e6e30d2a65eb5386c54f2a1fdabcd6299401))

- :robot: Format code with black
  ([`5ca03d1`](https://github.com/mycr0ft/sysmlpy/commit/5ca03d16ca9e6b99731b6aa7e2bb6611f4535398))

- :robot: Format code with black
  ([`57f8869`](https://github.com/mycr0ft/sysmlpy/commit/57f88699b6a158a5fbfdef2bb16789bfc491eb73))

- :robot: Format code with black
  ([`d308126`](https://github.com/mycr0ft/sysmlpy/commit/d308126637e563a0f0cee2bf4fd637acaadbbb0f))

- :robot: Format code with black
  ([`b32445c`](https://github.com/mycr0ft/sysmlpy/commit/b32445c85c7988a444bf875e35edb9e56b0ef84a))

- :robot: Format code with black
  ([`9871bdd`](https://github.com/mycr0ft/sysmlpy/commit/9871bdda7779362c2a0471d75b37798c7253b9e3))

- :robot: Format code with black
  ([`a6a8f1a`](https://github.com/mycr0ft/sysmlpy/commit/a6a8f1a20d6c5f9d160371346b3d141f5d86af04))

- :robot: Format code with black
  ([`400078b`](https://github.com/mycr0ft/sysmlpy/commit/400078b5398462758acc353c6a3ba08ad8920f93))

- :robot: Format code with black
  ([`b3fa4b1`](https://github.com/mycr0ft/sysmlpy/commit/b3fa4b11df364d4317abe80938464212b739faf5))

- :robot: Format code with black
  ([`e187adb`](https://github.com/mycr0ft/sysmlpy/commit/e187adb053f18d3546d559819a801be456026c39))

- :robot: Format code with black
  ([`8f1004f`](https://github.com/mycr0ft/sysmlpy/commit/8f1004fea06856f8fd79a4e91a37bdfc948461b3))

- :robot: Format code with black
  ([`bd4ad15`](https://github.com/mycr0ft/sysmlpy/commit/bd4ad15305dbf000f419e44f07d7db8f72afee12))

- :robot: Format code with black
  ([`1937b6e`](https://github.com/mycr0ft/sysmlpy/commit/1937b6ee8d446abdf52bb975cadc2b898d978c35))

- :robot: Format code with black
  ([`95a70fe`](https://github.com/mycr0ft/sysmlpy/commit/95a70feca54d696616c9a263e77d8d8ec75496e4))

- :robot: Format code with black
  ([`0ea0415`](https://github.com/mycr0ft/sysmlpy/commit/0ea04154d5e40630b8b9544616f0fc5be8de69e8))

- :robot: Format code with black
  ([`b87f1bf`](https://github.com/mycr0ft/sysmlpy/commit/b87f1bf92aa79b5b8c7f2f3224338e38dc63b470))

- :robot: Format code with black
  ([`2baf295`](https://github.com/mycr0ft/sysmlpy/commit/2baf295cc7863f7e6654d51108b77e3cbc3c6486))

- :robot: Format code with black
  ([`24e051d`](https://github.com/mycr0ft/sysmlpy/commit/24e051d8339c50c21ce173c364aa93fb96c0b633))

- :robot: Format code with black
  ([`4dcc4c9`](https://github.com/mycr0ft/sysmlpy/commit/4dcc4c9cc5ba70752934430f477f64a41f09ef16))

- :robot: Format code with black
  ([`1651fdb`](https://github.com/mycr0ft/sysmlpy/commit/1651fdbb80771a87afe94082df4a177adc37bc54))

- :robot: Format code with black
  ([`0b70bbc`](https://github.com/mycr0ft/sysmlpy/commit/0b70bbc00d82781d894fbf088d5e52831088c7ae))

- :robot: Format code with black
  ([`3cc027b`](https://github.com/mycr0ft/sysmlpy/commit/3cc027bbb04e7ddcbc3422f3b11b4809913f985b))

- :robot: Format code with black
  ([`f85c2a5`](https://github.com/mycr0ft/sysmlpy/commit/f85c2a51f49954e032322d4603bb431e53392c65))

- :robot: Format code with black
  ([`90398e1`](https://github.com/mycr0ft/sysmlpy/commit/90398e15bfcbc54d20011c35a9f9384da91fd134))

- :robot: Format code with black
  ([`dd46136`](https://github.com/mycr0ft/sysmlpy/commit/dd4613698f44e27b50ad427917683a68e9480857))

- :robot: Format code with black
  ([`27522bd`](https://github.com/mycr0ft/sysmlpy/commit/27522bd472d438fd31263443f3f529cb0b49bcf9))

- :robot: Format code with black
  ([`ea661dc`](https://github.com/mycr0ft/sysmlpy/commit/ea661dc4bc244f196ef2c13a15405a07220e51ca))

- :robot: Format code with black
  ([`a90c5e9`](https://github.com/mycr0ft/sysmlpy/commit/a90c5e946d25ff106cc6427b56ec9605a19e1532))

### :sparkles:

- :sparkles: Action definition with 2 of 4 tests complete.
  ([`9530eed`](https://github.com/mycr0ft/sysmlpy/commit/9530eed3aeda5bb059cdcff2555cc5c041d6e3bc))

- :sparkles: Add experimental ANTLR4 parser for SysML v2
  ([`5af2ec5`](https://github.com/mycr0ft/sysmlpy/commit/5af2ec51de42d24871210b56bc95b7f7ab630296))

- Add ANTLR4 Python runtime dependency - Download grammar from daltskin/sysml-v2-grammar (OMG
  v2026.03.0) - Generate Python parser from .g4 grammar files - Create antlr_parser.py with parse()
  and parse_file() functions - Create antlr_visitor.py to convert parse tree to textX-compatible
  dicts - Add load_antlr(), loads_antlr(), load_grammar_antlr() to public API - Update Model.load()
  to support both textX and ANTLR4 parsers - Fix Package.load_from_grammar() to handle various
  element types - Update Usage.load_from_grammar() for Requirement/UseCase formats - Add
  documentation in src/sysml2py/antlr/README.md - Update main README with new parser option

This provides a pure Python alternative to Java/TypeScript SysMLv2 parsers by using grammars
  auto-generated from the OMG specification.

- :sparkles: Added a new base model class to replace collapse function. Model will create packages
  and other custom classes for use. Additionally, packages can be created from grammar.
  ([`3dc5fca`](https://github.com/mycr0ft/sysmlpy/commit/3dc5fcad2e892b0e14c1c9f74cbea868df6844a5))

- :sparkles: Added all calculation grammar classes and tests that pass.
  ([`393fa4c`](https://github.com/mycr0ft/sysmlpy/commit/393fa4cce83471500401c3c7737a89c94e17f8cc))

- :sparkles: Added port with ability to create subfeatures with directionality.
  ([`94c0a19`](https://github.com/mycr0ft/sysmlpy/commit/94c0a19b08203a3db953858bf968de5c2f2084bc))

- :sparkles: Added some rollup classes the abstract underlying grammar. They have functions to
  manipulate the grammar.
  ([`b1e01a4`](https://github.com/mycr0ft/sysmlpy/commit/b1e01a465200e79f96a30da4f2ce5b861850ddd5))

- :sparkles: Adding analysis grammar and tests.
  ([`9400f9b`](https://github.com/mycr0ft/sysmlpy/commit/9400f9bef19757733b4d8a90d66f7e9678a42f6c))

- :sparkles: Adding constraint grammar and tests.
  ([`6212fd0`](https://github.com/mycr0ft/sysmlpy/commit/6212fd0fa4cd2261cd0b17e3871b5367080a0005))

- :sparkles: Adding first action definition grammar classes.
  ([`3454a50`](https://github.com/mycr0ft/sysmlpy/commit/3454a5048789917e7a4e02092ab3c602ba180157))

- :sparkles: Adding flow grammar and test.
  ([`4fe01c9`](https://github.com/mycr0ft/sysmlpy/commit/4fe01c9f2394bada05cc703f95177c90a32f37ee))

- :sparkles: Adding grammar for expressions.
  ([`f69c1ef`](https://github.com/mycr0ft/sysmlpy/commit/f69c1ef446730912ef9feb34638cde7596cc6ecc))

- :sparkles: Adding requirement grammar classes and tests.
  ([`0d73498`](https://github.com/mycr0ft/sysmlpy/commit/0d7349852aa361fe45ff5ffbc457226675f87b73))

- :sparkles: Flow Connector added to grammar and initial test built.
  ([`872b76d`](https://github.com/mycr0ft/sysmlpy/commit/872b76ded8c366f1b429968041f4214817395e1d))

- :sparkles: Migrate documentation from Sphinx to MkDocs
  ([`0f55e99`](https://github.com/mycr0ft/sysmlpy/commit/0f55e99b1afae3bac0e54a91b872d1d0ae50c526))

- Replace Sphinx (RST, autodoc) with MkDocs Material theme - Flatten docs/source/ into docs/ with
  symlinks to root-level docs - New mkdocs.yml with Material theme, light/dark mode, code copy - New
  docs/index.md landing page - Update release.yml CI workflow to use mkdocs build + gh-pages -
  Remove: conf.py, index.rst, Makefile, make.bat, IMPLEMENTATION_STATUS

- :sparkles: More badge for readme.
  ([`4be8d54`](https://github.com/mycr0ft/sysmlpy/commit/4be8d54efb78fa6030c8c80702f13e9ce295c5da))

- :sparkles: More tests and classes.
  ([`cd59e2e`](https://github.com/mycr0ft/sysmlpy/commit/cd59e2e7b2ff2c2eeb599480293f09efabcd79d9))

- :sparkles: More tests.
  ([`41d1f5e`](https://github.com/mycr0ft/sysmlpy/commit/41d1f5eb343c4afe02224fd6b9d68bed3f5cebaa))

- :sparkles: New package class.
  ([`3766690`](https://github.com/mycr0ft/sysmlpy/commit/3766690bd848de0475eb047af1870da358dd51ab))

- :sparkles: Partial addition of constraint grammar classes
  ([`5fc5c23`](https://github.com/mycr0ft/sysmlpy/commit/5fc5c23aea9b8c27a151dfa21f89f06d5a8a237d))

- :sparkles: State grammar classes initial implementation with first test.
  ([`61d3df1`](https://github.com/mycr0ft/sysmlpy/commit/61d3df1571b25e554bad631d005d11ce9ac5c0a4))

- :sparkles: State grammar with appropriate tests.
  ([`b896efe`](https://github.com/mycr0ft/sysmlpy/commit/b896efe2e0331383aa520621275ec8ae911f1871))

- :sparkles: v0.10.0 - 99% conformance pass rate (122/123), add get_definition() to 25+ grammar
  classes, fix visitor bugs, add state/requirement/constraint support
  ([`e5784d5`](https://github.com/mycr0ft/sysmlpy/commit/e5784d598002784b67b0db6554354f94841094ca))

- :sparkles: v0.11.0 - 100% conformance (123/123), rename project to sysmlpy
  ([`cd7818e`](https://github.com/mycr0ft/sysmlpy/commit/cd7818e2c8524ed26f1cbbbef0d27a251bdeecf5))

Grammar fixes: - Add LPAREN AS typeReference RPAREN for (as Type) cast syntax - Add ownedExpression
  DOT bodyExpression for lambda/filter expressions - Handle filterPackage imports in visitor - Fix
  interface_part UnboundLocalError - Add get_definition() to SuccessionFlowConnectionUsage - Add
  CaseDefinition to DefinitionElement dispatch - Fix UsageExtensionKeyword keyword field

Documentation: - Update README, STATUS, TODO, TUTORIAL for v0.11.0 - Update all conformance results
  to 100%

Rename: - sysml2py -> sysmlpy (package, imports, docs, CI/CD)

- :sparkles: v0.12.0 - Storage abstraction layer, graph backend, convenience functions
  ([`61222d0`](https://github.com/mycr0ft/sysmlpy/commit/61222d00dce600f40060cb70d9533c9033de7349))

New features: - Store protocol (ABC) with InMemoryStore and NetworkXStore backends - Element
  identity via stable UUIDs - Typed relationships (parent_child, typed_by, specializes, etc.) -
  Graph analysis: connected_components, cycles, centrality, shortest paths - Convenience functions:
  find_all, count, traverse, to_dict, to_graph, path_between - networkx as optional dependency: pip
  install sysmlpy[graph]

Bug fixes: - Parent references now set correctly for nested children in load_from_grammar -
  path_between handles list return from find()

Tests: - 82 new store tests (all pass) - 122 existing tests (all pass) - 37 conformance tests (all
  pass)

- :sparkles: v0.9.0 - Add explicit transition support and bump version
  ([`baf4cca`](https://github.com/mycr0ft/sysmlpy/commit/baf4ccac0b075f97794a67fe0647d56bc1b98118))

- Support 'transition name first X then Y;' syntax via TransitionUsageMember - Transition class now
  has .name, .source, and .target attributes - State.load_from_grammar() handles
  TransitionUsageMember alongside TargetTransitionUsageMember - Add .parent property to all elements
  (Usage, Model, Package, Transition) - Add State machine Python API (.transitions, .entry_actions,
  .exit_actions, .do_actions) - Fix EmptySuccessionMember/EmptySuccession null handling - Fix
  trigger extraction from PayloadParameter.children - Add get_definition() to PerformedActionUsage
  and PerformActionUsageDeclaration

### :white_check_mark:

- :white_check_mark: Add get_definition() to 18 grammar classes for conformance tests
  ([`2ae53f0`](https://github.com/mycr0ft/sysmlpy/commit/2ae53f07dce5b9fd276c8fe375637813f9ffd919))

- Added get_definition() to: BasicUsagePrefix, BindingConnector, EmptySuccession,
  EmptySuccessionMember, FlowEnd, FlowEndMember, FlowEndSubsetting, FlowFeature, FlowFeatureMember,
  FlowRedefinition, OccurrenceUsagePrefix, DefaultInterfaceEnd, OccurrenceDefinitionPrefix,
  EndFeatureUsage, EndUsagePrefix, ConnectorPart, BinaryConnectorPart, BasicDefinitionPrefix - Fixed
  EmptySuccession, EmptySuccessionMember, and BindingConnector __init__ to handle None/missing keys
  gracefully - simpletests conformance: 11/37 -> 16/37 passing (43%)

- :white_check_mark: Added final training example tests for action definition.
  ([`a399f5b`](https://github.com/mycr0ft/sysmlpy/commit/a399f5b295dd17de4979c3f2937f3016524ef8d6))

- :white_check_mark: Added test, updated workflow
  ([`b21d14b`](https://github.com/mycr0ft/sysmlpy/commit/b21d14bdff81269f58f648ae44cc87466385b328))

- :white_check_mark: Added two additional tests for expressions, tests all pass.
  ([`afae042`](https://github.com/mycr0ft/sysmlpy/commit/afae0426a30b4cebffec8a974c7b7823dbb80f3c))

- :white_check_mark: Adding child as optional to get def functions.
  ([`da90c49`](https://github.com/mycr0ft/sysmlpy/commit/da90c49e3b6d80258ea6bdc2391031ead534833f))

- :white_check_mark: Adding import test, namespaces are bugged.
  ([`6d35922`](https://github.com/mycr0ft/sysmlpy/commit/6d35922290ee468a3604102ce78da9f7f2846b36))

- :white_check_mark: Completed tests for state grammar.
  ([`2c2213c`](https://github.com/mycr0ft/sysmlpy/commit/2c2213cbc96b4fe16e66f680f3a10672f09f05d3))

- :white_check_mark: Correcting tests
  ([`fba8dce`](https://github.com/mycr0ft/sysmlpy/commit/fba8dcef847f4d5c39ad97c72b9cb711236df335))

- :white_check_mark: Fix AnalysisTest and add missing get_definition() methods
  ([`5eb1598`](https://github.com/mycr0ft/sysmlpy/commit/5eb15989c81d5bb7b01d925ee04b362b593dc488))

- Add analysisCaseUsage and caseUsage handling to _visit_usage_element_dict for top-level package
  member parsing - Fix visitor output: CaseUsageDeclaration -> CalculationUsageDeclaration - Fix
  visitor output: CaseBody ownedRelationship -> item - Rename Requirement.attributes ->
  req_attributes and Requirement.constraints -> req_constraints to avoid conflict with Searchable
  mixin properties - Add get_definition() to: SubjectMember, SubjectUsage, ObjectiveMember,
  ObjectiveRequirementUsage

simpletests conformance: 16/37 -> 19/37 passing (51%)

- :white_check_mark: Grammar changes now pass all tests.
  ([`7771f05`](https://github.com/mycr0ft/sysmlpy/commit/7771f053121a6edce9277b1de0536e2323d6276b))

- :white_check_mark: Package tests added.
  ([`803192b`](https://github.com/mycr0ft/sysmlpy/commit/803192b75749facc0d19cae596038663b3708714))

- :white_check_mark: Second example test for flow connector.
  ([`7d00034`](https://github.com/mycr0ft/sysmlpy/commit/7d00034efbfd60e993a69a697210896cab16cfb5))

### :zap:

- :zap: Adding code coverage badge to readme.
  ([`c72fe86`](https://github.com/mycr0ft/sysmlpy/commit/c72fe8699891d30a588abdafc27d3f030900a31a))

- :zap: Now loads from a single compiled grammar file that overwrites any previous grammar from
  imports.
  ([`2f90c7b`](https://github.com/mycr0ft/sysmlpy/commit/2f90c7b57a6a9e738601d42b75863bfd03f457bc))

- :zap: Removing commits to push off main, should not run into pull error for semantic parsing
  ([`77272f3`](https://github.com/mycr0ft/sysmlpy/commit/77272f3202378dbf637ad38c8e1cf69c68484198))

- :zap: Removing excess lines from code coverage.
  ([`442bc0c`](https://github.com/mycr0ft/sysmlpy/commit/442bc0c32048c9575de9f9025963bcca5f0bdfbc))

### Other

- :arrow_up: Fixing issue with dependencies and cython3 failing
  ([`bb4feb6`](https://github.com/mycr0ft/sysmlpy/commit/bb4feb6b4227c40a6f4b0f3d6cb6d87e43ec3565))

- :arrow_up: Fixing issue with dependencies for astropy
  ([`ac3b2ee`](https://github.com/mycr0ft/sysmlpy/commit/ac3b2ee6965e899854d4e0f4f1946a61bd4f9e67))

- :arrow_up: Merge from main and add astropy to main dependencies to handle units.
  ([`98f260b`](https://github.com/mycr0ft/sysmlpy/commit/98f260b888f54f9f6911b043387cd0fbc4d81c88))

- :art: Updating semantic parsing with lessons learned from windstorm
  ([`2f66dbf`](https://github.com/mycr0ft/sysmlpy/commit/2f66dbf4b023d05397d2fa5267d0ae4d29846f87))

- :bookmark: Bump version to 0.12.1 — test PyPI Trusted Publishing
  ([`81d38ce`](https://github.com/mycr0ft/sysmlpy/commit/81d38ceb0b850fa8e8a66b893b3952ca3866dba8))

- :clown: Adding workflows
  ([`e4cfccd`](https://github.com/mycr0ft/sysmlpy/commit/e4cfccd1660a608333f64f0549e52cd9cb3491fb))

- :clown: Rework into textx which has similar syntax to current standard.
  ([`b0f5991`](https://github.com/mycr0ft/sysmlpy/commit/b0f599120a4c2c2258011e610ad340072d02213e))

- :clown_face: First commit of some data
  ([`42c1782`](https://github.com/mycr0ft/sysmlpy/commit/42c1782455b44ea207e586993c7d362769f5b156))

- :construction_worker: Adding html to artifacts.
  ([`4b74045`](https://github.com/mycr0ft/sysmlpy/commit/4b74045fc81d32fe33629dc215d1126145f572c3))

- :construction_worker: Adding src to path for pytest in pyproject.toml
  ([`510d672`](https://github.com/mycr0ft/sysmlpy/commit/510d672b98c747c7ad573aa1d7fbf28d2252b4a1))

- :construction_worker: Corrected test directory again.
  ([`92d5dc2`](https://github.com/mycr0ft/sysmlpy/commit/92d5dc2c1bf1f416d6e248ddbf4bb45727a3e5fe))

- :construction_worker: Corrected test directory.
  ([`2bfc6df`](https://github.com/mycr0ft/sysmlpy/commit/2bfc6dfc1f6767a4caddd0e69fbc459fc5a0ed4a))

- :construction_worker: Fix to build script to include grammar files.
  ([`9a85d55`](https://github.com/mycr0ft/sysmlpy/commit/9a85d5547ba7c5343e1966d87d501583b2bc4c88))

- :fire: Getting rid of mac files.
  ([`b41512a`](https://github.com/mycr0ft/sysmlpy/commit/b41512a0aaea95c5a2791967ed01df9e67dba129))

- :fire: Removing mac files.
  ([`18174bd`](https://github.com/mycr0ft/sysmlpy/commit/18174bdc0d678666fa56e8a1233e7bd64a095a36))

- :green_heart: Adding autoformatting instead of checking
  ([`b7b38dc`](https://github.com/mycr0ft/sysmlpy/commit/b7b38dc71d7c0bdc4770d64fb7d2b3b79e8ad955))

- :green_heart: Adding Black linting
  ([`ee365ae`](https://github.com/mycr0ft/sysmlpy/commit/ee365aec7c3471a5843522a08c9afb951cef623c))

- :green_heart: Adding code coverage detection.
  ([`b977536`](https://github.com/mycr0ft/sysmlpy/commit/b977536f2a1289ef8a69a00ec4761e277d7a2c1b))

- :green_heart: Adding conftest.py
  ([`dbd32b9`](https://github.com/mycr0ft/sysmlpy/commit/dbd32b967febd7396de40ff7e73a9b75182e7507))

- :green_heart: Adding coveralls to all branches.
  ([`425024d`](https://github.com/mycr0ft/sysmlpy/commit/425024d1b7ebf80010c2f8a7e7d866b32ba4e5d8))

- :green_heart: Adding documentation to github action
  ([`124645c`](https://github.com/mycr0ft/sysmlpy/commit/124645c3b0629f15090da7a71b1315fce26ebd1d))

- :green_heart: Adding github actions back into commit.
  ([`e1ab9f4`](https://github.com/mycr0ft/sysmlpy/commit/e1ab9f4b7fa53591ce11de3f5813a67b7070dc8c))

- :green_heart: Adding path to init to correct test workflow.
  ([`d29bfb6`](https://github.com/mycr0ft/sysmlpy/commit/d29bfb6692d950bf384182dda96ebb017c8231af))

- :green_heart: Deployment fix and updates for pypi
  ([`ee89465`](https://github.com/mycr0ft/sysmlpy/commit/ee894656417cdf5be5f2126f0374d15377bd12c6))

- :green_heart: Fix for correct path to code coverage check.
  ([`2fccb2c`](https://github.com/mycr0ft/sysmlpy/commit/2fccb2c5333a8a5001854b1f759eef91c9d60c6e))

- :green_heart: Fixes for tests.
  ([`e11d3e9`](https://github.com/mycr0ft/sysmlpy/commit/e11d3e948c266bd6dc814cc68460f6d0bdc0e86a))

- :green_heart: Fixes to doc?
  ([`1f27b22`](https://github.com/mycr0ft/sysmlpy/commit/1f27b220215f9c91836b7f5945cc8e62ad3fcaf3))

- :green_heart: Fixes?
  ([`37fa8a5`](https://github.com/mycr0ft/sysmlpy/commit/37fa8a5bca43c05d4432cbfc894d30d4f0c8b6fc))

- :green_heart: Fixes?
  ([`1d57172`](https://github.com/mycr0ft/sysmlpy/commit/1d57172c96128dca989c7799c6b84ab22dd55b57))

- :green_heart: Fixes??
  ([`b414758`](https://github.com/mycr0ft/sysmlpy/commit/b4147584a2d74aa9cd910932e36f58f6c865df66))

- :green_heart: Fixes??
  ([`c6c0b0f`](https://github.com/mycr0ft/sysmlpy/commit/c6c0b0fdbf6db0924296fe5eb0a261be80d29667))

- :green_heart: Fixes???
  ([`2616e90`](https://github.com/mycr0ft/sysmlpy/commit/2616e900bc0cec252b7d04bce61f47740782f229))

- :green_heart: Fixes????
  ([`0955e8b`](https://github.com/mycr0ft/sysmlpy/commit/0955e8b6ee5ca7182ecd25a7a0fc80cea58b7dee))

- :green_heart: Fixing code coverage with better import flat file usage.
  ([`1a11479`](https://github.com/mycr0ft/sysmlpy/commit/1a114792dcce922388f014acb26e8691e3a4fe02))

- :green_heart: Fixing?
  ([`0f9b849`](https://github.com/mycr0ft/sysmlpy/commit/0f9b849174ca818f6de6076e4a8362ea32def4b6))

- :green_heart: Fixing??
  ([`21824c9`](https://github.com/mycr0ft/sysmlpy/commit/21824c9c0f34b6f436b84f257bf373ceaf8cf98d))

- :green_heart: I broke it.
  ([`38243bc`](https://github.com/mycr0ft/sysmlpy/commit/38243bce4125a204eb74f4692572731fc07c31eb))

- :green_heart: Ignore repo upload.
  ([`c5efb11`](https://github.com/mycr0ft/sysmlpy/commit/c5efb1139b987c89374ab3acf2586589e65d963e))

- :green_heart: Let's see if this breaks github actions.
  ([`3cf03e8`](https://github.com/mycr0ft/sysmlpy/commit/3cf03e82e64da027ffd9aa9f727ff0183cc2ee82))

- :green_heart: Let's see if this works, adding permissions in the script/
  ([`e21687a`](https://github.com/mycr0ft/sysmlpy/commit/e21687ad1f165f6da83b5ccca119f25bf2f885dc))

- :green_heart: Need more in req.txt
  ([`2a65bfc`](https://github.com/mycr0ft/sysmlpy/commit/2a65bfcbf1599ae8999735a02b99366950fbca3f))

- :green_heart: Removing distribute
  ([`2dd552e`](https://github.com/mycr0ft/sysmlpy/commit/2dd552e55097193d3cf6d181015c51a6b1fd795f))

- :green_heart: Seeing if I can drop the separate document workflow.
  ([`7692fc7`](https://github.com/mycr0ft/sysmlpy/commit/7692fc71ed63a03b3266f3408fbac56f12d5496b))

- :green_heart: Set write all
  ([`6ed68a0`](https://github.com/mycr0ft/sysmlpy/commit/6ed68a0149cd237eb8be070c3f63d8cc52ac278e))

- :green_heart: Test to check for new build changes to documentation.
  ([`382c9de`](https://github.com/mycr0ft/sysmlpy/commit/382c9debe679ef82abe288da8d1a26647c16bfd4))

- :green_heart: Testing if we need to change directory.
  ([`96fc0c5`](https://github.com/mycr0ft/sysmlpy/commit/96fc0c552930c697616caf7d9ef6fca68a1e4d77))

- :green_heart: Trying this for autoformat.
  ([`4fa5563`](https://github.com/mycr0ft/sysmlpy/commit/4fa5563b5a4e7e49f5807e979480d1346ae08379))

- :green_heart: Updating release workflow as well
  ([`8c72ce9`](https://github.com/mycr0ft/sysmlpy/commit/8c72ce97d613b4d59d0773bb8498cdeb8bbc992d))

- :green_heart: Updating test script to ensure available resources for pytest
  ([`6a9c297`](https://github.com/mycr0ft/sysmlpy/commit/6a9c29790e53f06e382d74f3b5e36bbfc1ed9de9))

- :poop Removing more excess files.
  ([`4bbe0f3`](https://github.com/mycr0ft/sysmlpy/commit/4bbe0f3a3e5795bb570cb378df8b4fb05f0f190c))

- :rocket: Moving to 0.1.0 baseline, most of the base functionality is here.
  ([`aa7333d`](https://github.com/mycr0ft/sysmlpy/commit/aa7333dffb77f364da4ee4f4c9375838e49d5568))

- :rocket: Moving to 0.1.2.
  ([`e6b7c2d`](https://github.com/mycr0ft/sysmlpy/commit/e6b7c2d92da8d0a26f4baf438c363fca75f4141c))

- :test_tube: Adding to coverage with failure tests.
  ([`7c2e96e`](https://github.com/mycr0ft/sysmlpy/commit/7c2e96eae65cb536027f01501b1dcc876d3a163e))

- :test_tube: Fix for test that can't find grammar.
  ([`18f7aca`](https://github.com/mycr0ft/sysmlpy/commit/18f7acab8be6b0d3d70ea7ee1f17fb8d3a11377d))

- :wastebasket: Remove BUGREPORT and BUGREPORT_20260516 folders
  ([`d879ca6`](https://github.com/mycr0ft/sysmlpy/commit/d879ca65b03b95d067ad1b50515de1a14cde45f1))
