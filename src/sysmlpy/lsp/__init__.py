# LSP package (v0.65.0 — Adoption Roadmap Goal 5)
#
# A minimal Language Server Protocol (LSP 3.17) implementation exposing
# sysmlpy's parse/analyze pipeline to editors:
#
#   textDocument/didOpen|didChange|didClose → publishDiagnostics
#   textDocument/hover | /documentSymbol | /definition | /completion
#
# Layout:
#   protocol.py — JSON-RPC Content-Length framing + LSP constants
#   server.py   — transport-agnostic language server (dict in → dict out)
#   stdio.py    — stdio transport; ``python -m sysmlpy.lsp`` entry point
#
# See docs/LSP.md for VS Code / Neovim wiring instructions.

from sysmlpy.lsp.protocol import (
    encode_message, read_message, ErrorCodes, SymbolKind,
)
from sysmlpy.lsp.server import Document, DocumentIndex, SysmlLanguageServer

__all__ = [
    "encode_message", "read_message", "ErrorCodes", "SymbolKind",
    "Document", "DocumentIndex", "SysmlLanguageServer",
]