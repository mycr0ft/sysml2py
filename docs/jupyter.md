# How-to: SysML v2 in Jupyter with the `%%sysml` magic

Write SysML v2 textual notation directly in notebook cells, keep a live
model in the session, query it from Python, and render PlantUML views —
powered by [sysmlpy](https://github.com/mycr0ft/sysmlpy), with no JVM and
no separate kernel install.

## 1. Install

```bash
pip install "sysmlpy[jupyter]"
# or, with the Poetry/uv project you are working in:
#   poetry add "sysmlpy[jupyter]"      /      uv add "sysmlpy[jupyter]"
```

The extra pulls in IPython ≥ 8. Everything else (parser, analyzer,
PlantUML generators) ships in sysmlpy core. JupyterLab/Jupyter Notebook
itself is assumed present (or install `sysmlpy[jupyter]` alongside your
normal `jupyterlab` install).

## 2. Load the extension

In the first cell of a notebook:

```python
%load_ext sysmlpy.ipython_magic
```

Successful load prints nothing. (If it errors with `No module named
IPython`, the `jupyter` extra is missing.)

## 3. Your first SysML cell

A `%%sysml` cell contains SysML v2 textual notation, not Python:

```
%%sysml
package Vehicle {
    part def Engine {
        attribute fuelRate : Real;
    }
    part def Vehicle {
        part engine : Vehicle::Engine;
    }
}
```

Output:

```
sysml: model updated — 1 package(s) loaded
```

The parsed model is **persistent across cells** and bound into the
notebook namespace as `model` (alias `_sysml`). Verify from a normal
Python cell:

```python
[p.name for p in model.packages]      # ['Vehicle']
model.find(name="Engine")             # exact declared-name search, any depth
engine = model.find(name="Engine", sysml_type="part")[0]
[a.name for a in engine.attributes]   # ['fuelRate']
model                                 # rich collapsible tree display
```

> **Name-lookup note:** `find`/`find_one` match an element's *declared
> name*, exactly, anywhere in the tree — `::` in a query is **not**
> interpreted as a path. If a package and a part share a name
> (`package Vehicle { part def Vehicle; }`), disambiguate with the type
> filter (`model.find(name="Vehicle", sysml_type="package")` vs
> `sysml_type="part"`), or navigate structurally from a unique anchor
> (`model.find_one("Engine").parent`), or use
> `model.path_between(src, dst)` / `model.traverse(cb)` for path-shaped
> queries. `find_one` raises `LookupError` rather than guessing when a
> name is ambiguous — treat that as a feature and narrow the query.

## 4. The iteration workflow

The natural loop is one `%%sysml` cell per element you are working on.
Re-declaring a package merges at **package-member granularity**: an
element with the same `name` + `sysml_type` replaces the prior
definition; sibling members are preserved.

```
%%sysml
package Vehicle {
    part def Vehicle {
        part engine : Vehicle::Engine;
        attribute mass : Real = 1500;
    }
}
```

```
sysml: model updated — 1 package(s) loaded, 1 redefined
```

`part def Engine` is still in the model — only `part def Vehicle` was
replaced. Parse errors are reported to stderr with line/column and
**never** discard the session model; fix the cell and re-run.

Options on the `%%sysml` line:

| Option | Effect |
|--------|--------|
| `--reset` | Discard the session model before parsing this cell |
| `--file PATH` | Parse SysML from a file instead of the cell body (use `-` as the cell body) |
| `--show` | Print the round-tripped (canonicalized) model text after merging |

## 5. Querying and visualizing

Line magics (modeled on the [OMG Pilot Implementation Jupyter
kernel](https://github.com/Systems-Modeling/SysML-v2-Pilot-Implementation/tree/master/org.omg.sysml.jupyter.kernel)
command set):

```
%sysml_reset                 # discard the session model
%sysml_list                  # list top-level packages
%sysml_list Engine           # elements matching an exact declared name
%sysml_show Engine           # AST dump rooted at a named element
%sysml_show Engine --json    # JSON representation when the dump parses
%sysml_viz Vehicle           # PlantUML view (default: general)
%sysml_viz Vehicle --view tree
```

`%sysml_viz` views: `general`, `interconnection`, `action`, `package`,
`tree`. Output is PlantUML text; render it with the PlantUML CLI, the
VS Code PlantUML extension, or a PlantUML server — e.g. paste into
<https://www.plantuml.com/plantuml>.

For anything richer, drop into Python — the model is a live object:

```python
model.find(sysml_type="part", recursive=False)   # top-level parts only
model.find(name="Engine")[0].attributes
pkg = model.find_one("Vehicle")
list(pkg)                                        # children
```

## 6. Semantic diagnostics

After each successful merge, sysmlpy's semantic analyzer runs
best-effort over the session model. Issues print to stderr as:

```
[semantic] [CODE] message
```

These are advisory (the model is still merged); use
`sysml-style check sysml/models/*.sysml` in CI for hard gating.

## 7. Saving your work

The magic edits the in-memory model. To persist back to `.sysml` files,
use `--show` to see canonical text and paste it into your model files, or
run the formatter from the shell:

```bash
sysmlpy format sysml/models/*.sysml
```

To package a model directory for interchange, see the
`.kpar` packaging how-to in the
[sysml-copier](https://github.com/mycr0ft/sysml-copier) template
(`scripts/make_kpar.py` in generated projects).

## 8. Troubleshooting

| Symptom | Cause / fix |
|---------|-------------|
| `No module named IPython` | Install the extra: `pip install "sysmlpy[jupyter]"` |
| `%%sysml is a cell magic, but the cell body is empty` | IPython requires a body; with `--file`, put `-` in the body |
| `find_one: 2 matches for 'X'` | X names both a package and an element — use a qualified name or `model.find(name=..., sysml_type=...)` |
| `unknown view '...'` | `%sysml_viz --view` accepts general\|interconnection\|action\|package\|tree |
| Session model looks stale/corrupted | `%sysml_reset`, then re-run your definition cells |
| Diagrams show as raw PlantUML text | Render with PlantUML (CLI/server/extension); the magic emits text by design |

## Command reference

The complete magic-command set of the OMG Pilot Implementation Jupyter
kernel (`%eval`, `%list`, `%show`, `%viz`, `%view`, `%export`, `%load`,
`%publish`, `%projects`, `%repo`, `%help`, `%exit`) and the mapping to
this implementation is documented in
[sysml-magics.md](sysml-magics.md).