# sysmlpy

A pure Python implementation for parsing, analyzing, and rendering
SysML v2.0 models. Uses the ANTLR4 parser for full SysML v2 grammar
support.

**Current release:** v0.77.0 — see [CHANGELOG](CHANGELOG.md).

## Highlights

- **123/123 OMG XPect parse conformance** and 143/143 grammar round-trip tests
- **Semantic analysis** with 31 rule codes: symbol resolution, imports,
  OCL well-formedness, type- and unit-checked expressions, `*`/`/`
  unit-dimension derivation, state machines, requirements, traceability
- **17 PlantUML views** + Java-free [boxes](https://github.com/mycr0ft/boxes)
  rendering (Unicode-braille text and SVG)
- **CLI suite**: `parse`, `analyze`, `diff`, `view`, `format`, `trace`,
  `export`/`import`, `eval`, `sim`, `xlsx` — CI-friendly exit codes
- **Storage backends**: memory, NetworkX, Kùzu (Cypher), Cayley (HTTP)
- **State-machine simulation** with real guard evaluation
- **Semantic model diff** between SysML files

## Quick Links

### Getting started
- [Tutorial](TUTORIAL.md) — comprehensive guide with class mapping tables
- [Quick Start](quickstart.md) — basic usage examples

### Reference
- [Project Summary](PROJECT_SUMMARY.md) — architecture and capabilities
- [Status](STATUS.md) — conformance results, rule-code catalogue, round-trip coverage
- [Changelog](CHANGELOG.md) — release history
- [Roadmap / TODO](TODO.md) — what's next
- [Guard Conditions](GUARDS.md) — the `if` transition keyword, done right
- [Boxes-backed Visualizer](boxes_view.md) — native UML shapes via `diagramboxes`
- [Simulation](sim.md) — state-machine simulation (`sysmlpy sim`)

### Tooling
- [LSP](LSP.md) — language server for editors
- [LSP Editor Setup](LSP_EDITORS.md) — per-editor integration guides
- [PlantUML Examples](plantuml-examples/) — rendered view gallery

### Archive
- [Archive](archive/README.md) — historical documents (PySysML2 comparison,
  completed development plan, reference analyses). No longer maintained.

## Installation

```bash
pip install sysmlpy
```

Optional extras:

```bash
pip install sysmlpy[graph]    # NetworkX graph analysis
pip install sysmlpy[kuzu]     # Kùzu embedded graph database
pip install sysmlpy[cayley]   # Cayley graph database client
pip install sysmlpy[xlsx]     # Excel export
pip install sysmlpy[sim]      # State-machine simulation
```

## Basic Usage

```python
from sysmlpy import loads, Part, Attribute

model = loads("""
package Vehicle {
    part def Engine;
    part engine1 : Engine { attribute mass = 100 [kg]; }
}
""")

engine = model.find_one("engine1")
print(engine.dump())

# Semantic analysis
from sysmlpy import analyze
issues = analyze(model)
print(issues.summary())
```

Command line:

```bash
sysmlpy analyze model.sysml     # semantic gate with CI exit codes
sysmlpy view model.sysml        # PlantUML / Markdown / HTML views
sysmlpy diff old.sysml new.sysml
```

See the [README](https://github.com/mycr0ft/sysmlpy#command-line-tools)
for the complete CLI table.