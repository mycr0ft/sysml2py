# sysmlpy Language Server (LSP)

*(v0.65.0 — Adoption Roadmap Goal 5)*

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
| `completion` | SysML v2 keywords + every named element in the model |
| Text sync | Full-document sync (`didOpen` / `didChange` / `didClose`) |

Position encoding is UTF-16 (LSP default).

### Diagnostic fidelity (honest limits)

* Syntax errors carry exact positions from the ANTLR error listener.
* Semantic issues carry **no source positions** in sysmlpy's model
  representation, so the server locates them by searching the text for
  the names quoted in the issue message (falling back to the owning
  element's name, then to line 1). This is a pragmatic heuristic, not a
  position-tracked parser; the `UNRESOLVED_EXPRESSION_IDENTIFIER` class
  of issues resolves precisely, structural warnings resolve to their
  nearest name occurrence.

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
  hover and diagnostics always agree.
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
poetry run pytest tests/lsp_test.py -q
```

The suite covers framing round-trips (incl. non-ASCII payloads and
malformed headers), the full lifecycle (initialize → features →
shutdown → exit), diagnostics ranges, every feature, an in-memory
stdio session, and a real subprocess run of `python -m sysmlpy.lsp`.

## Follow-ups (tracked in TODO.md)

* Incremental text sync (`TextDocumentSyncKind.INCREMENTAL`)
* Position-accurate semantic diagnostics (requires parser position
  tracking — a larger visitor change)
* `workspace/symbol` + multi-file workspace support
* Completion after `.` (member completion via type resolution)
* Debounced re-parse for very large documents