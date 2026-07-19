# boxes-backed State-Machine Visualizer

`sysmlpy.boxes_view` is an **optional** renderer that produces a
[`boxes`](https://github.com/mycr0ft/boxes) Diagram from a parsed SysML v2
`state def`. It complements `as_state_transition_view()` (the PlantUML
renderer) by producing native UML shapes — rounded-corner `«state»` boxes,
filled-circle initial pseudostate, bullseye final state, orthogonal
port-to-port routing — without needing a Java runtime or a PlantUML server.

## Install

`boxes` is an optional dependency. From the sysmlpy checkout:

```bash
poetry run pip install -e ../boxes
```

or, if you have boxes on PyPI / a wheel:

```bash
pip install boxes
```

`import sysmlpy` keeps working without `boxes` installed — the new
symbols are lazy-loaded on first access and raise an informative
`ImportError` if `boxes` is missing.

## Public API

```python
import sysmlpy

# Build an in-memory boxes.Diagram you can introspect or further decorate
d = sysmlpy.as_state_transition_view_boxes(model, focus=None)

# Render straight to the terminal (braille characters)
print(sysmlpy.render_state_transition_view(model, routing="orthogonal"))

# Render to an SVG string
svg = sysmlpy.render_state_transition_view_svg(model, routing="orthogonal")
open("state.svg", "w").write(svg)
```

`model` accepts raw SysML text, a `sysmlpy.Model`, or the dict from
`sysmlpy.load_grammar()`. `focus` chooses a specific `state def` by name
when multiple are present in the same source.

The pseudostate shape classes are re-exported so diagram-author code
can use the state-machine vocabulary directly:

```python
from sysmlpy.boxes_view import (
    InitialPseudostate, JunctionPseudostate,
    ChoicePseudostate, ForkPseudostate, JoinPseudostate,
    FinalState, TerminatePseudostate,
    HistoryPseudostate, EntryPoint, ExitPoint, StateNode,
)
```

## What the adapter handles

The adapter walks the visitor dict and emits one round-cornered StateNode
per `state X` declaration, one `InitialPseudostate` (filled black circle)
for `entry; then X;`, and one `FinalState` (bullseye) the first time a
transition targets the reserved `done` name. Transitions are emitted as
edges labelled with `Trigger [guard]`.

| SysML v2 construct | Adapter output |
|---|---|
| `state def X { … }` | one diagram per `state def` (use `focus=` to choose) |
| `entry; then X;` | `InitialPseudostate` → edge (no arrowhead) → first state |
| `state A;` | `StateNode` with `«state»` stereotype, rounded corners |
| `entry action warmup : WarmUp;` / `do monitor;` / `exit act;` | attributes `entry / warmup`, `do / monitor`, `exit / act` in the state box |
| `transition T first A accept Trig if guard do Effect then B;` | one edge A → B with label `Trig [guard]` |
| `accept X then Y;` (shorthand succession) | synthesized transition with trigger `X`, target `Y`, source back-filled from the most-recently declared state in the region |
| `transition first A accept X then done;` | edge to a synthesized `FinalState` bullseye (one per region, reused if multiple transitions hit `done`) |
| `transition first A accept X then S2.S3;` | full feature-chain resolution — endpoint correctly identified as the nested substate `S2.S3` |
| `state Composite { state A; state B; transition first A accept X then B; }` | composite state emitted as a StateNode; substates emitted as namespace-qualified siblings (`Composite.A`, `Composite.B`). Recursive — supports arbitrary nesting depth |
| `state R parallel { state A; state B; }` (`isParallel=true`) | composite state carries both `«state»` and `«parallel»` stereotypes |

## The SysML v2 pseudostate landscape

The UML / SysML 1.x menagerie of *pseudostates* — `initial`, `final`,
`terminate`, `junction`, `choice`, `fork`, `join`, shallow-history,
deep-history, entry-point, exit-point — was deliberately collapsed in
SysML v2. The formal spec (`formal/26-03-02`, Sept 2025, §7.18) keeps only:

- **Initial** — not a named shape; expressed as a succession from the
  state's (possibly empty) entry action: `entry; then X;`
- **Final** — the reserved transition target `done`. Spec §7.18:
  *"a transition to `done` indicates that the source state is the final
  state of the containing state performance."*
- **Parallel** — the `parallel` keyword on a StateDefBody marks
  orthogonal regions composition (no transitions allowed between
  concurrent substates)
- **Guarded choice** — UML 1.x's choice and junction pseudostates are
  replaced by `if guard then target` conditional successions

The following UML 1.x / SysML 1.x state pseudostates have **no token
in the lexer, no production in the grammar, and no class in the Ecore
metamodel**, and are correspondingly not emitted by the adapter:

| Removed pseudostate | What replaces it in SysML v2 |
|---|---|
| Junction | guarded transitions |
| Choice | `if guard then target` conditional successions |
| Shallow history | (none — not in the language) |
| Deep history | (none — not in the language) |
| Entry point | (none — composite states are entered directly) |
| Exit point | (none — composite states are exited directly) |
| Terminate | `done` (final) covers the common case |
| Fork / Join | moved to **action flow** (`fork-node`, `join-node` in §8.2.2.14.1), not state machines |

The `boxes` package still ships first-class `JunctionPseudostate`,
`ChoicePseudostate`, `ForkPseudostate`, `JoinPseudostate`,
`HistoryPseudostate`, `EntryPoint`, `ExitPoint`, `TerminatePseudostate`
classes so you can build SysML 1.x / UML-style diagrams by hand when you
need them — they just aren't emitted by the SysML v2 adapter because the
source language has no equivalent input.

## Example: the OMG StateTest.sysml state machine

```python
import sysmlpy

text = """state def S {
    entry; then S1;
    state S1;
        accept s : Sig then S2;
    state S2 { state S3; }
    accept Exit then done;
    transition
        first S1
        accept s : Sig
        then S2.S3;
}"""

print(sysmlpy.render_state_transition_view(text, routing="orthogonal"))
```

The output is a braille-character diagram showing:

- a filled black circle (initial pseudostate)
- a `«state» S1` box → `«state» S2` (with shorthand `accept s : Sig` edge)
- a `«state» S3` substate (sibling of S2 visually; nesting is a future
  layout enhancement)
- a `«state» S1` → `«state» S3` edge for the explicit `transition first S1 … then S2.S3`
- an `Exit` edge from S1 (the most-recent declared state at that point
  in the region) to a bullseye final state

Use `render_state_transition_view_svg(...)` to produce a vector SVG
instead, suitable for embedding in docs or editing by hand.

## Limitations / future work

- **Composite nesting is currently visual-sibling**, not visuallyenclosed
  — boxes lays out substates as top-level nodes with
  namespace-qualified names (`Composite.A`). True UML "substates inside
  the parent box" rendering builds on the `View.children` infrastructure
  in `boxes` and is a focused future enhancement.
- **Edge labels are best-effort** — complex guard expressions other than
  a single `QualifiedName` are currently dropped to keep the diagram
  readable. Trivial to extend if needed.
- **`state usage` (top-level `state x :> StateDef parallel { … }`)** —
  parsed fine, but the adapter currently only descends into `StateDefinition`
  bodies. A small extension handles `StateUsage` top-level — beyond what
  the typical state-machine test fixture exercises.