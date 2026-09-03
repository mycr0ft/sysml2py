// sysmlpy-lsp — VS Code extension wiring for the sysmlpy language server.
//
// Plain JavaScript (no build step): open this folder, run `npm install`,
// then F5 (Run Extension) to launch an Extension Development Host, or
// `npx vsce package` to produce a .vsix.
//
// The server is spawned with stdio. Resolution order:
//   1. `sysmlpy.serverPath` setting (must point to an executable that
//      speaks LSP over stdio — typically the `sysmlpy-lsp` console
//      script installed with sysmlpy, or an absolute path)
//   2. fallback: `python -m sysmlpy.lsp` using the interpreter on PATH

const vscode = require('vscode');
const {
  LanguageClient, LanguageClientOptions, ServerOptions, TransportKind,
} = require('vscode-languageclient/node');

let client;

function serverOptions() {
  const cfg = vscode.workspace.getConfiguration('sysmlpy');
  const extra = cfg.get('serverArgs') || [];
  const serverPath = cfg.get('serverPath');
  if (serverPath) {
    return {
      command: serverPath,
      args: extra,
      transport: TransportKind.stdio,
    };
  }
  return {
    command: 'python',
    args: ['-m', 'sysmlpy.lsp', ...extra],
    transport: TransportKind.stdio,
  };
}

function activate(context) {
  const clientOptions = {
    documentSelector: [{ language: 'sysml', scheme: 'file' }],
    synchronize: {
      // reload the server when its settings change
      configurationSection: 'sysmlpy',
    },
  };
  client = new LanguageClient(
    'sysmlpy',
    'SysML v2 (sysmlpy)',
    serverOptions(),
    clientOptions
  );
  context.subscriptions.push(client.start());
}

function deactivate() {
  if (client) {
    return client.stop();
  }
  return undefined;
}

module.exports = { activate, deactivate };