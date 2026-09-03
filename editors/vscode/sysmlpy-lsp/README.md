# sysmlpy-lsp — VS Code extension

SysML v2 language support powered by [sysmlpy](https://github.com/mycr0ft/sysmlpy):
live diagnostics (syntax + semantic), document outline, hover
(kind/type/value), go-to-definition, and keyword/member completion.

## Prerequisites

- sysmlpy ≥ 0.65.0 installed (e.g. `pipx install sysmlpy` or
  `pip install sysmlpy`) so the `sysmlpy-lsp` console script is on PATH —
  verify with `sysmlpy-lsp --version`
- Node.js + npm (only for installing the extension itself)

## Run from source (development)

```bash
cd editors/vscode/sysmlpy-lsp
npm install
code .   # then press F5 to open an Extension Development Host
```

Open any `*.sysml` file; the extension spawns the language server
automatically.

## Package a .vsix

```bash
cd editors/vscode/sysmlpy-lsp
npx vsce package
code --install-extension sysmlpy-lsp-0.65.0.vsix
```

## Configuration

| Setting | Default | Meaning |
|---|---|---|
| `sysmlpy.serverPath` | `sysmlpy-lsp` | Server executable (or set to e.g. `/path/to/venv/bin/sysmlpy-lsp`) |
| `sysmlpy.serverArgs` | `[]` | Extra server args, e.g. `["--log", "/tmp/lsp.log"]` for protocol traces |
| `sysmlpy.trace.server` | `off` | LSP client-side tracing in the Output panel |

If `sysmlpy.serverPath` is empty, the extension falls back to
`python -m sysmlpy.lsp` with the interpreter found on PATH.

## Troubleshooting

- **No diagnostics?** Run `sysmlpy-lsp --version` in a terminal — if it
  fails, sysmlpy is not installed into the environment VS Code uses.
- **Check server logs**: set `sysmlpy.serverArgs` to
  `["--log", "/tmp/sysmlpy-lsp.log"]` and inspect that file; the log
  contains every framed JSON-RPC message both ways.