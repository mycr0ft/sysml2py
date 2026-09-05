# sysmlpy Language Server (LSP)

*(v0.65.0 — Adoption Roadmap Goal 5; batch 4 enhancements v0.83.0)*

sysmlpy ships a [Language Server Protocol](https://microsoft.github.io/language-server-protocol/)
server that brings parse/analyze diagnostics and model navigation into
any LSP-capable editor — VS Code, Neovim, Emacs, Sublime, …

```bash
sysmlpy-lsp --version          # console script (installed with sysmlpy)
python -m sysmlpy.lsp          # equivalent
sysmlpy-lsp --log /tmp/lsp.log # protocol trace for debugging
```

## Capabilities

| LSP capability | Behavior |
|---|---|
| `publishDiagnostics` | On open/change: **syntax errors** with exact ANTLR line:column ranges, plus **semantic issues** from `analyze()` (errors/warnings) located in the text |
| `documentSymbol` | Hierarchical model outline (packages → defs → features) with kind icons (`Package`, `Class`, `Field`, …) and `part def`/`: Type` details |
| `hover` | Markdown card: element kind, name, qualified name, `typed by: Type`, literal value (via the grammar object's `get_value()`) |
| `definition` | Go-to-declaration: usage name → its declaration; type name (in `part w : T`) → the type's definition |
| `completion` | SysML v2 keywords + every named element; after ``base.`` the members of the resolved type of *base* (typed part, or a definition named directly) |
| `workspace/symbol` | Case-insensitive substring query across all open documents plus `*.sysml` files under the initialized workspace root (cached until the next document change) |
| Text sync | **Incremental** (`didOpen` / `didChange` with LSP ranges); range-less changes are still accepted as full-document replacements |

Position encoding is UTF-16 (LSP default).

### Diagnostic fidelity (honest limits)

* Syntax errors carry exact positions from the ANTLR error listener.
* Semantic issues are **position-tracked by source-order pairing**
  (v0.83.0): the symbol walk visits model elements in declaration
  order, so the *n*-th element with a given `(kind, name)` is paired
  with the *n*-th declaration occurrence of that pair in the text —
  an issue about `Fleet::Engine` points at the right `part def Engine`
  even when several share the name.  Issues whose element cannot be
  located fall back to the quoted-`'name'`-occurrence heuristic, then
  to line 1.  True parser-side position tracking (annotating visitor
  dicts with ANTLR token positions) remains future work.
* While a document is transiently unparsable (e.g. a half-typed
  expression), outline/hover/definition degrade to empty results, but
  `completion` keeps working: member resolution falls back to the last
  successfully parsed model, and the keyword/name fallback list is
  built from that model too.

## Architecture

```
editor (VS Code / Neovim)                 stdio JSON-RPC (Content-Length framing)
        │  ▲
        ▼                                  ▼
  extension/nvim-lsp        sysmlpy.lsp.stdio (transport, logging)
        │                              │ dicts
        │                    sysmlpy.lsp.server.SysmlLanguageServer
        │                              │
        │              DocumentIndex: sysmlpy.parse() + sysmlpy.analyze()
        │                              → diagnostics / symbol tree / features
```

* **Transport-agnostic core** — `SysmlLanguageServer.handle_message()`
  maps message dicts to message dicts; `protocol.py` implements the
  byte-stream framing; `stdio.py` glues them. All 37 protocol tests run
  in-process against a `BytesIO` pipe plus one subprocess smoke test.
* One `DocumentIndex` per document version caches the parse + analysis
  snapshot; every feature handler reads that snapshot, so outline,
  hover and diagnostics always agree.  The server additionally keeps
  each document's *last successfully parsed model* (surviving
  re-indexing on every keystroke) so `completion` keeps resolving
  members while the text is transiently broken.
* `analyze()` failures are swallowed (issues become the diagnostics
  that did parse) — the analyzer must never crash the editor session.

## Editor setup

### VS Code

A ready-to-package extension lives in
[`editors/vscode/sysmlpy-lsp/`](../editors/vscode/sysmlpy-lsp/README.md)
(plain JS, no build step):

```bash
cd editors/vscode/sysmlpy-lsp && npm install && code .   # F5 → dev host
# or
npx vsce package && code --install-extension sysmlpy-lsp-*.vsix
```

### Neovim (0.11+, built-in LSP)

```lua
-- ~/.config/nvim/lua/sysml.lua  (or init.lua)
vim.filetype.add({ extension = { sysml = "sysml" } })

vim.lsp.config("sysmlpy", {
  cmd = { "sysmlpy-lsp" },          -- or { "python", "-m", "sysmlpy.lsp" }
  filetypes = { "sysml" },
  root_markers = { ".git", "sysml.lock" },
})
vim.lsp.enable("sysmlpy")
```

Open a `.sysml` file — `:lua vim.diagnostic.setloclist()` shows issues,
K hovers, `gd` jumps to definitions, `:Pickers -> symbols` outlines.

### Neovim (0.8–0.10, nvim-lspconfig)

```lua
local lspconfig = require("lspconfig")
local configs = require("lspconfig.configs")
if not configs.sysmlpy then
  configs.sysmlpy = {
    default_config = {
      cmd = { "sysmlpy-lsp" },
      filetypes = { "sysml" },
      root_dir = lspconfig.util.find_git_ancestor,
    },
  }
end
lspconfig.sysmlpy.setup({})
```

### Other editors

Any client that can spawn a stdio LSP server works. Point it at:

```
cmd: sysmlpy-lsp        (or: python -m sysmlpy.lsp)
root detection: none required (single-file server)
```

## Testing

```bash
poetry run pytest tests/lsp_test.py tests/lsp_batch4_test.py -q
```

The suite covers framing round-trips (incl. non-ASCII payloads and
malformed headers), the full lifecycle (initialize → features →
shutdown → exit), diagnostics ranges, every feature, an in-memory
stdio session, and a real subprocess run of `python -m sysmlpy.lsp`.
The batch-4 suite adds incremental-sync edits (UTF-16 positions,
clamping, mixed full+range changes), source-order diagnostic pairing,
workspace scans, and `.`-member completion over transiently broken
documents.

## Follow-ups (tracked in TODO.md)

* ~~Incremental text sync~~ *(shipped v0.83.0)*
* ~~`workspace/symbol` + multi-file workspace support~~ *(shipped
  v0.83.0 — root scan, not yet cross-file symbol resolution)*
* ~~Completion after `.` (member completion via type resolution)~~
  *(shipped v0.83.0 — direct members; inherited members and library
  types fall back to the full list)*
* True parser-side position tracking for semantic diagnostics
  (annotating visitor dicts with ANTLR token positions — a larger
  visitor change; the current source-order pairing covers the common
  cases)
* Debounced re-parse for very large documents
* Cross-file go-to-definition across workspace roots