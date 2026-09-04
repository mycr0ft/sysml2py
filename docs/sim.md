# State-Machine Simulation (`sysmlpy sim`)

Cameo-style simulation for SysML v2 `state def` machines: the model's
machine becomes executable — triggers fire transitions, guards are
evaluated **for real** against the model's attribute values (pint-aware,
via the v0.64 expression evaluator), effects are logged, and the live
state is shown while you drive.

Requires the optional `sim` extra:

```bash
poetry install -E sim          # or: pip install 'sysmlpy[sim]'
```

## Quickstart

Model (`examples/sim/cruise_controller.sysml`):

```sysml
package Sim {
    attribute speed : ScalarValues::Real := 30;
    attribute key : ScalarValues::Boolean := true;

    action def logState;
    action def hold;

    state def Cruise {
        entry; then off;
        state off;
        state engaged;
        state holding;
        state slowing;
        transition engage first off accept Engage when key do logState then engaged;
        transition hold first engaged accept SpeedOK do hold then holding;
        transition slow first holding accept Decel when speed > 40 do logState then slowing;
        transition resume first slowing accept SpeedOK then holding;
        transition stop first holding accept Off when speed <= 5 then off;
        transition cancel first engaged accept Cancel then off;
    }
}
```

Interactive TUI:

```bash
sysmlpy sim examples/sim/cruise_controller.sysml
```

```
State machine Cruise — current: 'off'
  > off
    engaged
    holding
    slowing
transitions from here:
  0) Engage when key -> (target)  [guard: TRUE]
commands: <n> fire · <Trigger> fire · step · set name=value · values · log · q
> set speed=70
> Engage
State machine Cruise — current: 'engaged'
...
```

Scripted (for demos and CI):

```bash
sysmlpy sim examples/sim/cruise_controller.sysml \
    --run "Engage; SpeedOK; Decel; SpeedOK; Off; Cancel" --set speed=70
```

```text
Engage: fired -> 'engaged'
SpeedOK: fired -> 'holding'
Decel: fired -> 'slowing'
SpeedOK: fired -> 'holding'
Off: blocked -> 'holding'      # speed=70, guard `speed <= 5` is false
Cancel: blocked -> 'holding'   # Cancel only leaves 'engaged'
```

## Python API

```python
from sysmlpy import loads
from sysmlpy.sim import StateSimulator

sim = StateSimulator(model, focus="Cruise")
sim.state                     # 'off'
sim.available()               # [('Engage', 'key', True)] — (trigger, guard, passes now)
sim.send("Engage")            # True -> state 'engaged'
sim.set_value("speed", 70)    # what-if override for guards
sim.step()                    # fire the first enabled transition
sim.log                       # every fired/blocked attempt, with guard results
sim.reset()                   # back to the initial state, log cleared
```

## Semantics

- **Initial state** from `entry; then X;` (the official initial-point
  shorthand).  Machines without one start in the first declared state
  (a note is reported).
- **Triggers** (`accept <Signal>`) fire when sent; a trigger carried by
  several transitions from the current state falls through the guards
  in declaration order (first guard that holds wins).
- **Completion transitions** (no `accept`) fire automatically on
  entering a state (UML run-to-completion) and manually via `step()`.
- **Guards** (`when <expr>`) evaluate against the model's attribute
  values (`collect_values`, pint `Quantity`-aware) plus `set_value`
  overrides; a guard that cannot evaluate blocks the transition and is
  logged.
- **Effects** (`do <action>`) are logged as text — behavior
  references round-trip (`do logState` → `logState`), and the
  send/assignment forms surface their declarations (`send Alert to
  logger`, `x := 5`).
- **Composite states** expand with qualified names
  (`Composite.Sub`): a transition targeting a composite enters its
  initial substate (UML default entry), the region runs its own
  transitions, and a transition declared on the composite applies
  from every substate — deeper transitions win the fall-through.

## Scope of the MVP

- Parallel regions raise `SimulationError` (top-level or inside a
  composite).  Substates referenced by bare name from outside their
  region are flattened implicitly, with a note.
- One machine per simulator (`--focus` picks which); parallel regions
  raise `SimulationError` for now.
- Effects are logged, not executed; effect-side assignments (their
  `target := value` text is now available) would flow through
  `set_value` and are a follow-up.  Composite regions and parallel
  regions are flat/raise for now (the descriptor carries the
  composites).

## Library choice

Execution delegates to [`transitions`](https://pypi.org/project/transitions/)
(the `sim` extra).  It builds machines from *data* at runtime —
`Machine(model=…, states=[…], transitions=[{...}])` — which is exactly
the shape of the SysML-model → machine bridge, and its guards
(`conditions`) and effects (`before`/`after`) map 1:1 onto the SysML
guard/effect features.  The runner-up, `python-statemachine`, prefers
declarative class definitions, which is awkward for arbitrary parsed
models; a hand-rolled kernel remains a fallback if deep SysML
semantics (do-actions over time, `after` deadlines, history) outgrow
it.