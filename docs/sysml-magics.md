# SysML v2 Jupyter Magic Commands — Reference

Two implementations of notebook SysML exist in the ecosystem:

1. **The OMG Pilot Implementation kernel** (`org.omg.sysml.jupyter.kernel`,
   Java/Xtext, installed via Miniconda from
   <https://github.com/Systems-Modeling/SysML-v2-Pilot-Implementation>) — a
   full [Jupyter kernel](https://github.com/Systems-Modeling/SysML-v2-Pilot-Implementation/blob/master/org.omg.sysml.jupyter.kernel/README.adoc)
   where SysML is the *language of the notebook itself*.
2. **`sysml_magic.py`** (this template) — an IPython extension providing a
   `%%sysml` cell magic in the ordinary Python kernel, backed by
   [sysmlpy](https://github.com/mycr0ft/sysmlpy). Pure Python, no JVM.

This document records the official Pilot Implementation magic commands
(extracted from `SysMLInteractive.java` and `SysMLInteractiveHelp.java`)
and what this template's magic supports for each.

## Official Pilot Implementation commands

| Magic | Purpose (per `%help <cmd>` strings in the Pilot source) |
|-------|----------------------------------------------------------|
| `%help [<COMMAND>]` | List available commands, or detailed help on one. |
| `%eval [--target=<NAME>] <EXPR>` | Evaluate an expression, optionally in the scope of a named (fully qualified) element. |
| `%list [<QUERY>]` | With no argument, list all loaded library packages. With `<QUERY>` (a legal `import` name: `N`, `N::*`, `N::**`, optionally followed by a `[filter]`), list matching elements. |
| `%show [--style=<STYLE>] <NAME>` | Print the abstract syntax tree rooted at `<NAME>`. Styles: `TREE` (indented), `JSON`. |
| `%publish [-d] [--project=<P>] [--branch=<B>] <NAME>` | Publish the elements rooted at `<NAME>` to the model repository. `-d` includes derived properties. |
| `%viz [--view=<VIEW>] [--style=<STYLE>...] <NAME>...` | PlantUML visualization. Views: `DEFAULT`, `TREE` (≈BDD), `INTERCONNECTION` (≈IBD), `STATE`, `ACTION`, `SEQUENCE`, `MIXED`. Styles include `LR`, `ortholine`, … (delegated to `SysML2PlantUMLStyle`). |
| `%view [--render=<RENDERING>] [--style=<STYLE>...] <NAME>` | Render a *view usage* defined in the model itself. Renderings: same set as `%viz` views. |
| `%export <NAME>` | Write a JSON file of the AST rooted at `<NAME>`. |
| `%load [--id=<ID>] [--name=<N>] [--branch=<B>] [<NAME>]` | Download previously published models from the repository. |
| `%projects` | List projects in the repository (name + UUID). |
| `%repo [<BASE PATH>]` | Set/print the repository API base path used by `%publish`/`%load`/`%projects`. |
| `%exit` | (Console/REPL mode only) leave the interactive session. |

The Pilot kernel additionally reads `$ISYSML_API_BASE_PATH` and
`$ISYSML_GRAPHVIZ_PATH` environment variables (also settable via
`--api-base-path` / `--graphviz-path`) to locate the repository API and the
Graphviz `dot` binary used by `%viz`.

## `sysml_magic` support in this template

The ordinary-Python-kernel magic implements the interaction patterns that
make sense client-side, backed by sysmlpy instead of the Eclipse/EMF stack.
Repository-backed commands (`%publish`, `%load`, `%projects`, `%repo`)
require the OMG API server and are out of scope; use the Pilot kernel if you
need them.

| Official command | This template | Notes |
|------------------|---------------|-------|
| (SysML cell) | `%%sysml [--reset] [--file PATH] [--show]` | Cell body is SysML source. Accumulates into a persistent `model`. Package members merge by (name, sysml_type): re-declared elements replace, others are preserved. |
| `%help` | `%%sysml?` / module docstring | `help(sysml_magic)` or the docstrings. |
| `%list [<QUERY>]` | `%sysml_list [NAME]` | No arg: top-level packages. With a name: exact-name matches at any depth. Richer queries: `model.find(sysml_type='part', recursive=False)` from Python. |
| `%show [--style] <NAME>` | `%sysml_show NAME [--json]` | `dump()` tree text, or full JSON with `--json`. |
| `%viz [--view] [--style] <NAME>` | `%sysml_viz NAME [--view V]` | Views: `general`, `interconnection`, `action`, `package`, `tree` (sysmlpy PlantUML generators). Output is PlantUML text; render with the PlantUML CLI/extension, or embed via a PlantUML server. |
| `%eval <EXPR>` | Python cells directly | The model is a live Python object (`model`, alias `_sysml`); evaluate with plain Python. |
| `%view <NAME>` | not yet | Requires sysmlpy View/Viewpoint rendering; planned. |
| `%export <NAME>` | `%sysml_show NAME --json` | Prints JSON; redirect to a file if needed. |
| `%publish` / `%load` / `%projects` / `%repo` | not supported | Requires the OMG API repository service. |
| `%exit` | n/a | Jupyter manages the session. |

## Session semantics

- The first `%%sysml` cell creates `model` and binds it into the notebook
  namespace (as `model` and `_sysml`).
- Each subsequent cell is parsed fresh and **merged** into the session model
  at *package-member* granularity: a member with the same `name` and
  `sysml_type` replaces the old one; everything else is kept. So you can
  iterate on a single part definition in one cell without re-stating the
  rest of the package.
- Parse errors are reported to stderr with line/column and **do not** discard
  the session model — fix and re-run the cell.
- `%%sysml --reset` (or `%sysml_reset`) starts over from an empty model.
- Semantic diagnostics from sysmlpy's analyzer run after each merge and
  surface as `[semantic] [code] message` on stderr.

## Known differences from the Pilot kernel

- Names must be matched exactly as declared (sysmlpy `find`); the Pilot
  kernel additionally supports filter expressions in `[]` after `::*`.
- `%viz` styles are limited to sysmlpy's PlantUML generator options
  (`style="bw"` etc.), not the full OMG style matrix.
- No repository integration (publish/load/projects/repo).
- Only `%%sysml` cells are SysML; everything else is Python. The Pilot kernel
  inverts this (everything is SysML unless it's a `%...` command).