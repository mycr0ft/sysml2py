# Using the sysmlpy LSP in Neovim and VS Code

*A practical setup guide (sysmlpy ≥ 0.65.0). For capability tables and
architecture see [`LSP.md`](LSP.md).*

---

## 0. Install the language server (once)

The server is part of sysmlpy. Any editor setup starts with making sure
the `sysmlpy-lsp` executable is reachable from the editor's environment:

```bash
pip install sysmlpy          # or: pipx install sysmlpy
sysmlpy-lsp --version        # → 0.65.0
```

If `sysmlpy-lsp` isn't found, either fix your PATH or configure the
editor to launch `python -m sysmlpy.lsp` instead (both recipes below
show how). `python -m sysmlpy.lsp --log /tmp/lsp.log` writes a full
protocol trace — your best debugging tool.

---

## VS Code

The repo ships a ready-to-package extension:
[`editors/vscode/sysmlpy-lsp/`](../editors/vscode/sysmlpy-lsp/).

### Option A — run from source (fastest way to try it)

```bash
git clone https://github.com/mycr0ft/sysmlpy && cd sysmlpy
cd editors/vscode/sysmlpy-lsp && npm install && code .
# press F5 → "Extension Development Host" window opens
```

Open any `.sysml` file in the dev host — diagnostics, outline, hover
and go-to-definition work immediately.

### Option B — install as a .vsix

```bash
cd editors/vscode/sysmlpy-lsp
npx vsce package                     # → sysmlpy-lsp-0.65.0.vsix
code --install-extension sysmlpy-lsp-0.65.0.vsix
```

### Settings

| Setting (prefix `sysmlpy.`) | Default | Meaning |
|---|---|---|
| `serverPath` | `sysmlpy-lsp` | Server executable. Set to an absolute path if your venv isn't on VS Code's PATH. Leave empty to fall back to `python -m sysmlpy.lsp`. |
| `serverArgs` | `[]` | Extra args, e.g. `["--log", "/tmp/lsp.log"]` |
| `trace.server` | `off` | Client-side LSP trace in the *Output → SysML v2 (sysmlpy)* panel |

### What you get

| Key / UI | Feature |
|---|---|
| red/yellow squiggles on save & type | syntax errors (exact positions) + semantic errors/warnings |
| Outline view / `Ctrl+Shift+O` | model outline: packages → defs → attributes |
| hover (`Ctrl+K Ctrl+I`) | `part def Vehicle`, `typed by: Real`, literal values |
| `F12` / `Ctrl+Click` | go-to-definition (usage → decl, type name → `part def T`) |
| typing inside the file | keyword + member completion (`Ctrl+Space`) |

> The extension registers the `sysml` language for `*.sysml` files with
> bracket/comment/folding rules, so syntax highlighting plugins that
> rely on a TextMate grammar keep working alongside.

---

## Neovim

Neovim has a built-in LSP client — no plugin required. Everything below
goes in `~/.config/nvim` (Lua).

### Neovim 0.11+ (current built-in API)

```lua
-- 1) file type association
vim.filetype.add({ extension = { sysml = "sysml" } })

-- 2) server configuration
vim.lsp.config("sysmlpy", {
  cmd = { "sysmlpy-lsp" },            -- or: { "python", "-m", "sysmlpy.lsp" }
  filetypes = { "sysml" },
  root_markers = { ".git", "sysml.lock" },
})

-- 3) enable it
vim.lsp.enable("sysmlpy")
```

Out of the box you get: diagnostics in the gutter/signcolumn
(`vim.diagnostic.open_float()` under the cursor), hover with `K`,
go-to-definition with `gd`, document symbols via
`vim.lsp.buf.document_symbol()`, and completion through your completion
plugin (nvim-cmp/blink.cmp read LSP completions automatically).

Handy keymap block if you don't have one:

```lua
vim.api.nvim_create_autocmd("LspAttach", {
  callback = function(args)
    local opts = { buffer = args.buf }
    vim.keymap.set("n", "K", vim.lsp.buf.hover, opts)
    vim.keymap.set("n", "gd", vim.lsp.buf.definition, opts)
    vim.keymap.set("n", "<space>s", vim.lsp.buf.document_symbol, opts)
    vim.keymap.set("n", "<space>d", vim.diagnostic.setloclist, opts)
  end,
})
```

Verify with `:checkhealth vim.lsp` / `:lua print(vim.lsp.get_clients()[1].name)`
— it should report `sysmlpy` attached to your `.sysml` buffer.

### Neovim 0.8–0.10 (nvim-lspconfig)

```lua
local lspconfig = require("lspconfig")
local configs = require("lspconfig.configs")

vim.filetype.add({ extension = { sysml = "sysml" } })

if not configs.sysmlpy then
  configs.sysmlpy = {
    default_config = {
      cmd = { "sysmlpy-lsp" },            -- or { "python", "-m", "sysmlpy.lsp" }
      filetypes = { "sysml" },
      root_dir = lspconfig.util.find_git_ancestor,
      settings = {},
    },
  }
end
lspconfig.sysmlpy.setup({})
```

### Troubleshooting (Neovim)

| Symptom | Check |
|---|---|
| `:LspInfo` shows no client | `sysmlpy-lsp` not on PATH for nvim's environment — use `cmd = { "/abs/path/sysmlpy-lsp" }` |
| No diagnostics | run `python -m sysmlpy.lsp --log /tmp/lsp.log`, edit the file, inspect the log for framed traffic |
| Completion not showing | nvim's built-in client doesn't auto-trigger; bind `vim.lsp.buf.completion()` or use nvim-cmp with `lsp` source |

---

## Both editors: what diagnostics look like

Given this file:

```
package VehicleSpec {
    part def Vehicle {
        attribute mass : Real := 1200;
        attribute speed : Real := 25.0;
        constraint c1 { mass > missing }
    }
}
```

you'll see:

* **squiggle on `missing`** — `Unresolved identifier 'missing' in
  expression of Attribute 'c1'` (error)
* **warnings on `Real`** — *Standard library type 'Real' used without
  explicit import; add `import ScalarValues::Real;`* (fix: add the
  import line)
* **outline** shows `VehicleSpec → Vehicle → {mass, speed, c1}`

## Known limits

* Semantic diagnostics are position-tracked by source-order pairing
  (v0.83.0) — the *n*-th element with a given `(kind, name)` maps to
  the *n*-th declaration occurrence in the text; unlocatable elements
  fall back to name search. Syntax errors are exact.
* Single-file scope: cross-file definitions resolve only if they are
  imported into the same file.
* INCREMENTAL text sync (v0.83.0) — the server applies ranged edits
  and re-parses; very large models (>10k lines) may still want
  editor-side debouncing.
* While a document is transiently unparsable, completion keeps working
  through the last successfully parsed model; outline/hover/definition
  degrade to empty until the text parses again.