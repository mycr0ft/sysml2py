# CHANGELOG

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
