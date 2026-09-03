# -*- coding: utf-8 -*-
"""sysmlpy language server core (v0.65.0 — Adoption Roadmap Goal 5).

A transport-agnostic LSP server: ``SysmlLanguageServer.handle_message``
takes a decoded JSON-RPC message dict and returns the response and/or
notification dicts to send back, in order.  The stdio transport
(:mod:`sysmlpy.lsp.stdio`) is responsible for framing and I/O; tests
feed dicts directly.

Feature summary
---------------
- ``initialize`` / ``initialized`` / ``shutdown`` / ``exit`` lifecycle
- ``textDocument/didOpen|didChange|didClose`` with FULL sync, publishing
  diagnostics (syntax errors with precise ANTLR line:column ranges;
  semantic issues located heuristically in the text)
- ``textDocument/hover``          — kind/type/value summary
- ``textDocument/documentSymbol`` — hierarchical model outline
- ``textDocument/definition``     — jump to declaration
- ``textDocument/completion``     — SysML keywords + model member names

Design notes
------------
* ``SemanticIssue`` carries no source positions (the parser does not
  track line/col for model dicts), so semantic diagnostics locate their
  range by searching the document text for the names mentioned in the
  issue message (quoted ``'name'`` occurrences, then the owning
  element's name).  Syntax errors use the ANTLR listener's exact
  ``line:column``.  See docs/LSP.md for the trade-off discussion.
* Positions are UTF-16 code-unit based (the LSP default encoding).
* The analyzer must never crash the editor: every feature handler is
  wrapped so failures degrade to empty results, and ``reparse`` guards
  ``analyze()`` separately from ``parse()``.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from sysmlpy.lsp.protocol import ErrorCodes, SymbolKind

DIAGNOSTIC_SOURCE = "sysmlpy"

# sysml_type (element.sysml_type) → declaration keyword as written in text
_KIND_KEYWORD = {
    "package": "package",
    "part": "part",
    "item": "item",
    "attribute": "attribute",
    "port": "port",
    "action": "action",
    "state": "state",
    "transition": "transition",
    "constraint": "constraint",
    "requirement": "requirement",
    "calculation": "calc",
    "connection": "connection",
    "flow": "flow",
    "allocation": "allocation",
    "verification": "verification",
    "concern": "concern",
    "view": "view",
    "viewpoint": "viewpoint",
    "rendering": "rendering",
    "metadata": "metadata",
    "enumeration": "enum",
    "occurrence": "occurrence",
    "interface": "interface",
    "message": "message",
    "succession": "succession",
}

_COMPLETION_KEYWORDS = [
    "abstract", "accept", "action", "allocation", "attribute", "bind",
    "calc", "comment", "concern", "connection", "constraint", "derived",
    "doc", "do", "end", "entry", "enumeration", "exit", "exhibit", "false",
    "flow", "import", "in", "individual", "inout", "interface", "item",
    "message", "metadata", "nonunique", "null", "occurrence", "ordered",
    "out", "package", "part", "perform", "port", "readonly", "redefines",
    "rendering", "requirement", "satisfy", "send", "specializes", "state",
    "succession", "termination", "then", "transition", "true", "verify",
    "verification", "view", "viewpoint", "variation",
]


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------


def _utf16_len(text: str) -> int:
    """Length of *text* in UTF-16 code units (LSP default position encoding)."""
    return sum(2 if ord(ch) > 0xFFFF else 1 for ch in text)


def _word_at(text_line: str, utf16_col: int) -> Optional[Tuple[str, int]]:
    """Return ``(word, start_char_index)`` for the identifier at *utf16_col*.

    *start_char_index* is a Python character index into *text_line*.
    """
    # UTF-16 column → python char index.
    col = 0
    units = 0
    while col < len(text_line) and units < utf16_col:
        units += 2 if ord(text_line[col]) > 0xFFFF else 1
        col += 1
    if col >= len(text_line) or not (text_line[col].isalnum()
                                     or text_line[col] == "_"):
        return None
    start = col
    while start > 0 and (text_line[start - 1].isalnum()
                         or text_line[start - 1] == "_"):
        start -= 1
    end = col
    while end < len(text_line) and (text_line[end].isalnum()
                                    or text_line[end] == "_"):
        end += 1
    return text_line[start:end], start


def _severity_number(severity: str) -> int:
    """SemanticIssue severity string → LSP DiagnosticSeverity number."""
    return {"error": 1, "warning": 2, "information": 3,
            "info": 3, "hint": 4}.get(severity, 3)


# ---------------------------------------------------------------------------
# Document
# ---------------------------------------------------------------------------


class Document:
    """An open text document (one SysML source file)."""

    def __init__(self, uri: str, text: str, version: Optional[int] = None,
                 language_id: str = "sysml"):
        self.uri = uri
        self.text = text
        self.version = version
        self.language_id = language_id
        self._lines: List[str] = text.splitlines()

    def update(self, text: str, version: Optional[int] = None) -> None:
        self.text = text
        if version is not None:
            self.version = version
        self._lines = text.splitlines()

    @property
    def lines(self) -> List[str]:
        return self._lines

    def line_text(self, line: int) -> str:
        return self._lines[line] if 0 <= line < len(self._lines) else ""


# ---------------------------------------------------------------------------
# Symbol entries
# ---------------------------------------------------------------------------


class SymbolEntry:
    """A model element located in the document text."""

    __slots__ = ("name", "kind_label", "sysml_type", "is_definition",
                 "line", "start_col", "end_col", "typed_by_name",
                 "qualified", "children")

    def __init__(self, name: str, kind_label: str, sysml_type: str,
                 is_definition: bool, line: int, start_col: int,
                 end_col: int, typed_by_name: Optional[str] = None):
        self.name = name
        self.kind_label = kind_label
        self.sysml_type = sysml_type
        self.is_definition = is_definition
        self.line = line
        self.start_col = start_col          # python char index
        self.end_col = end_col              # python char index (exclusive)
        self.typed_by_name = typed_by_name
        self.qualified = ""
        self.children: List["SymbolEntry"] = []


def _lsp_symbol_kind(entry: SymbolEntry) -> int:
    """Map a sysml element to an LSP SymbolKind."""
    t = entry.sysml_type
    if t == "package":
        return SymbolKind.PACKAGE
    if entry.is_definition:
        if t == "enumeration":
            return SymbolKind.ENUM
        if t in ("port", "interface"):
            return SymbolKind.INTERFACE
        return SymbolKind.CLASS
    if t in ("enumeration", "state"):
        return SymbolKind.ENUM_MEMBER
    if t == "attribute":
        return SymbolKind.FIELD
    if t in ("action", "calculation"):
        return SymbolKind.FUNCTION
    return SymbolKind.VARIABLE


# ---------------------------------------------------------------------------
# DocumentIndex — parse/analyze + text location of model elements
# ---------------------------------------------------------------------------


class DocumentIndex:
    """Parsed state of one document: model, diagnostics, symbol index.

    Built once per document version via :meth:`reparse`; diagnostics and
    all feature handlers (hover/definition/symbols/completion) read from
    this single snapshot so every feature agrees on one parse.
    """

    def __init__(self, document: Document):
        self.document = document
        self.model = None
        self.diagnostics: List[Dict[str, Any]] = []
        self.symbols: List[SymbolEntry] = []
        self._by_name: Dict[str, List[SymbolEntry]] = {}
        self._child_ids: set = set()
        self.reparse()

    # -- build ---------------------------------------------------------------

    def reparse(self) -> None:
        """Re-parse the document and rebuild diagnostics + symbols."""
        import sysmlpy

        doc = self.document
        self.symbols = []
        self._by_name = {}
        self._child_ids = set()
        self.diagnostics = []

        model, errors = sysmlpy.parse(doc.text)
        self.model = model

        for err in errors:
            diag = self._syntax_diagnostic(err)
            if diag is not None:
                self.diagnostics.append(diag)

        if model is not None:
            try:
                issues = sysmlpy.analyze(model)
            except Exception:  # analyzer must never break the editor
                issues = []
            for issue in issues:
                diag = self._semantic_diagnostic(issue)
                if diag is not None:
                    self.diagnostics.append(diag)
            self._build_symbols()

    # -- diagnostics ---------------------------------------------------------

    def _syntax_diagnostic(self, err: str) -> Optional[Dict[str, Any]]:
        """Convert ``"Syntax error at L:C: msg"`` into an LSP diagnostic."""
        import re

        m = re.match(r"Syntax error at (\d+):(\d+): (.*)", err, re.DOTALL)
        if not m:
            return self._zero_range_diagnostic(err, "syntax", 1)
        line = max(0, int(m.group(1)) - 1)      # ANTLR lines are 1-based
        col = max(0, int(m.group(2)))           # ANTLR columns are 0-based
        line_text = self.document.line_text(line)
        end_col = max(col + 1, _utf16_len(line_text))
        return {
            "range": {"start": {"line": line, "character": col},
                      "end": {"line": line, "character": end_col}},
            "severity": 1,
            "source": DIAGNOSTIC_SOURCE,
            "code": "syntax",
            "message": m.group(3).strip(),
        }

    def _zero_range_diagnostic(self, message: str, code: str,
                               severity: int) -> Dict[str, Any]:
        return {
            "range": {"start": {"line": 0, "character": 0},
                      "end": {"line": 0, "character": 1}},
            "severity": severity,
            "source": DIAGNOSTIC_SOURCE,
            "code": code,
            "message": message,
        }

    def _semantic_diagnostic(self, issue) -> Optional[Dict[str, Any]]:
        """Locate a SemanticIssue in the text and build its diagnostic.

        Strategy: scan the issue message for quoted names (``'foo'``) and
        try each until one occurs in the text as a whole word; fall back
        to the owning element's name, then to a zero-range at (0, 0).
        """
        import re

        message = issue.message or ""
        candidates = re.findall(r"'([^']+)'", message)
        element_name = getattr(issue.element, "name", None)
        if element_name and element_name not in candidates:
            candidates.append(element_name)
        severity = _severity_number(issue.severity)
        for name in candidates:
            loc = self._locate_word(name)
            if loc is not None:
                line, start_col, end_col = loc
                return {
                    "range": {
                        "start": {"line": line, "character": start_col},
                        "end": {"line": line, "character": end_col},
                    },
                    "severity": severity,
                    "source": DIAGNOSTIC_SOURCE,
                    "code": issue.code,
                    "message": message,
                }
        return self._zero_range_diagnostic(message, issue.code, severity)

    def _locate_word(self, name: str) -> Optional[Tuple[int, int, int]]:
        """Find *name* as a whole word → ``(line, utf16_start, utf16_end)``."""
        import re

        pattern = re.compile(rf"\b{re.escape(name)}\b")
        for lineno, line_text in enumerate(self.document.lines):
            m = pattern.search(line_text)
            if m:
                return (lineno, _utf16_len(line_text[:m.start()]),
                        _utf16_len(line_text[:m.end()]))
        return None

    # -- symbols -------------------------------------------------------------

    def _build_symbols(self) -> None:
        """Walk the model tree and locate each named element in the text."""
        if self.model is None:
            return

        def walk(element, parents: Tuple[str, ...]) -> None:
            for child in getattr(element, "children", []) or []:
                name = getattr(child, "name", None)
                if not name:
                    continue
                entry = self._make_entry(child, name, parents)
                if entry is not None:
                    walk_children(child, entry, parents + (name,))

        def walk_children(element, entry, path) -> None:
            self.symbols.append(entry)
            self._by_name.setdefault(entry.name, []).append(entry)
            for sub in getattr(element, "children", []) or []:
                sub_name = getattr(sub, "name", None)
                if not sub_name:
                    continue
                sub_entry = self._make_entry(sub, sub_name, path)
                if sub_entry is not None:
                    entry.children.append(sub_entry)
                    walk_children(sub, sub_entry, path + (sub_name,))

        # Top-level children of the model root.
        for child in getattr(self.model, "children", []) or []:
            name = getattr(child, "name", None)
            if not name:
                continue
            entry = self._make_entry(child, name, ())
            if entry is not None:
                walk_children(child, entry, (name,))

        for e in self.symbols:
            for c in e.children:
                self._child_ids.add(id(c))

    def _make_entry(self, element, name, parents) -> Optional[SymbolEntry]:
        sysml_type = getattr(element, "sysml_type", None) or "element"
        keyword = _KIND_KEYWORD.get(sysml_type, sysml_type)
        is_def = bool(getattr(element, "is_definition", False))
        loc = self._locate_declaration(keyword, name, is_def)
        if loc is None:
            return None
        line, start_col, end_col = loc
        entry = SymbolEntry(
            name=name,
            kind_label=f"{keyword}{' def' if is_def else ''}",
            sysml_type=sysml_type,
            is_definition=is_def,
            line=line,
            start_col=start_col,
            end_col=end_col,
            typed_by_name=getattr(element, "typed_by_name", None),
        )
        entry.qualified = "::".join(parents + (name,))
        return entry

    def _locate_declaration(self, keyword: str, name: str,
                            is_definition: bool
                            ) -> Optional[Tuple[int, int, int]]:
        """Find the ``<keyword> [def] <name>`` declaration in the text.

        Returns ``(line, start_char, end_char)`` with *start/end* being
        Python character indices spanning the *name* token; falls back to
        any whole-word occurrence (usages, aliases, anonymous decls).
        """
        pattern = re.compile(
            rf"\b{re.escape(keyword)}\s+(?:def\s+)?(?P<name>{re.escape(name)})\b"
        )
        for lineno, line_text in enumerate(self.document.lines):
            m = pattern.search(line_text)
            if m:
                return (lineno, m.start("name"), m.end("name"))
        return self._locate_word(name)

    # -- features ------------------------------------------------------------

    def symbol_at(self, line: int, utf16_col: int
                  ) -> Optional[Tuple[SymbolEntry, str]]:
        """Resolve the identifier under the cursor to a symbol entry.

        Returns ``(entry, word)``, preferring a *definition* on a
        different line than the cursor (jump-to-def semantics).
        """
        line_text = self.document.line_text(line)
        found = _word_at(line_text, utf16_col)
        if not found:
            return None
        word, _start = found
        entries = self._by_name.get(word)
        if not entries:
            return None
        for prefer in (lambda e: e.line != line and e.is_definition,
                       lambda e: e.line != line,
                       lambda e: True):
            for e in entries:
                if prefer(e):
                    return e, word
        return None

    def hover(self, line: int, utf16_col: int) -> Optional[Dict[str, Any]]:
        """LSP hover for the symbol under the cursor (or ``None``)."""
        hit = self.symbol_at(line, utf16_col)
        if hit is None:
            return None
        entry, _word = hit
        parts = [f"**{entry.kind_label}** `{entry.name}`"]
        if entry.typed_by_name:
            parts.append(f"\n\n- typed by: `{entry.typed_by_name}`")
        if "::" in entry.qualified:
            parts.append(f"\n- qualified: `{entry.qualified}`")
        value = self._literal_value(entry)
        if value is not None:
            parts.append(f"\n- value: `{value}`")
        return {"contents": {"kind": "markdown",
                             "value": "".join(parts)}}

    def _literal_value(self, entry: SymbolEntry):
        """Best-effort literal value for a usage element (never raises)."""
        if self.model is None or entry.is_definition:
            return None
        try:
            el = self.model.find_one(entry.name, sysml_type=entry.sysml_type)
        except Exception:
            return None
        if el is None:
            return None
        try:
            return el.get_value()
        except Exception:
            return None

    def definition(self, line: int, utf16_col: int) -> Optional[Dict[str, Any]]:
        """LSP Location for the declaration under the cursor (or ``None``)."""
        hit = self.symbol_at(line, utf16_col)
        if hit is None:
            return None
        entry, _word = hit
        return {
            "uri": self.document.uri,
            "range": {
                "start": {"line": entry.line, "character": entry.start_col},
                "end": {"line": entry.line, "character": entry.end_col},
            },
        }

    def document_symbols(self) -> List[Dict[str, Any]]:
        """Hierarchical DocumentSymbol array (roots = top-level elements)."""
        roots = [e for e in self.symbols if id(e) not in self._child_ids]
        return [self._to_document_symbol(e) for e in roots]

    def _to_document_symbol(self, entry: SymbolEntry) -> Dict[str, Any]:
        detail = entry.kind_label + (
            f" : {entry.typed_by_name}" if entry.typed_by_name else ""
        )
        return {
            "name": entry.name,
            "detail": detail,
            "kind": _lsp_symbol_kind(entry),
            "range": self._symbol_range(entry),
            "selectionRange": {
                "start": {"line": entry.line, "character": entry.start_col},
                "end": {"line": entry.line, "character": entry.end_col},
            },
            "children": [self._to_document_symbol(c) for c in entry.children],
        }

    def _symbol_range(self, entry: SymbolEntry) -> Dict[str, Any]:
        """Estimate a full range by brace balancing from the decl line."""
        depth = 0
        seen_open = False
        last = entry.line
        for lineno in range(entry.line, len(self.document.lines)):
            line_text = self.document.line_text(lineno)
            opens = line_text.count("{")
            depth += opens - line_text.count("}")
            if opens:
                seen_open = True
            last = lineno
            if seen_open and depth <= 0:
                break
            if not seen_open and lineno > entry.line:
                break  # brace-less statement: range is its own line
        return {
            "start": {"line": entry.line, "character": entry.start_col},
            "end": {"line": last, "character": 0},
        }

    def completion(self) -> List[Dict[str, Any]]:
        """Completion items: SysML keywords + every named model element."""
        items = [
            {"label": kw, "kind": 14, "detail": "SysML keyword"}
            for kw in _COMPLETION_KEYWORDS
        ]
        seen = set()
        for entry in self.symbols:
            if entry.name in seen:
                continue
            seen.add(entry.name)
            items.append({
                "label": entry.name,
                "kind": _lsp_symbol_kind(entry),
                "detail": entry.kind_label,
            })
        return items


# ---------------------------------------------------------------------------
# Language server
# ---------------------------------------------------------------------------


class SysmlLanguageServer:
    """Transport-agnostic LSP server: message dict in → message dicts out.

    ``handle_message`` returns the response (for requests) and any
    notifications generated, in send order.
    """

    def __init__(self) -> None:
        self.docs: Dict[str, Document] = {}
        self.indexes: Dict[str, DocumentIndex] = {}
        self.client_capabilities: Dict[str, Any] = {}
        self.initialized = False
        self.shutdown_requested = False
        self.exited = False
        self.server_capabilities = {
            "positionEncoding": "utf-16",
            "textDocumentSync": {"openClose": True, "change": 1},  # FULL
            "hoverProvider": True,
            "definitionProvider": True,
            "documentSymbolProvider": True,
            "completionProvider": {"triggerCharacters": [":", "."],
                                   "resolveProvider": False},
        }

    # -- dispatch ------------------------------------------------------------

    def handle_message(self, msg: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process one JSON-RPC message; return messages to send."""
        method = msg.get("method")
        msg_id = msg.get("id")

        if method is None:
            return []  # a response to a server request — we send none

        if method == "exit":
            self.exited = True
            return []

        if method == "shutdown":
            self.shutdown_requested = True
            return [self._ok(msg_id, None)]

        if self.shutdown_requested and msg_id is not None:
            return [self._error(msg_id, ErrorCodes.INVALID_REQUEST,
                                "Server is shutting down")]

        handler = self._HANDLERS.get(method)
        if handler is None:
            if msg_id is not None:
                return [self._error(msg_id, ErrorCodes.METHOD_NOT_FOUND,
                                    f"Method not found: {method}")]
            return []  # unknown notification — ignore silently

        if method != "initialize" and not self.initialized \
                and msg_id is not None:
            return [self._error(msg_id, ErrorCodes.SERVER_NOT_INITIALIZED,
                                "Server not initialized")]

        try:
            return handler(self, msg, msg_id)
        except Exception as exc:  # never kill the transport
            if msg_id is not None:
                return [self._error(msg_id, ErrorCodes.INTERNAL_ERROR,
                                    f"{type(exc).__name__}: {exc}")]
            return []

    # -- lifecycle -------------------------------------------------------------

    def _handle_initialize(self, msg, msg_id):
        params = msg.get("params") or {}
        self.client_capabilities = params.get("capabilities") or {}
        self.initialized = True
        return [self._ok(msg_id, {"capabilities": self.server_capabilities})]

    def _handle_initialized(self, msg, msg_id):
        return []

    # -- document sync -----------------------------------------------------------

    def _handle_did_open(self, msg, msg_id):
        td = (msg.get("params") or {}).get("textDocument") or {}
        uri = td.get("uri")
        if not uri:
            return []
        self.docs[uri] = Document(uri, td.get("text", ""),
                                  td.get("version"),
                                  td.get("languageId", "sysml"))
        self.indexes.pop(uri, None)
        return [self._publish(uri)]

    def _handle_did_change(self, msg, msg_id):
        params = msg.get("params") or {}
        uri = (params.get("textDocument") or {}).get("uri")
        doc = self.docs.get(uri)
        if doc is None:
            return []
        changes = params.get("contentChanges") or []
        if changes:
            # FULL sync: the last change carries the whole document.
            doc.update(changes[-1].get("text", doc.text),
                       params.get("textDocument", {}).get("version"))
        self.indexes.pop(uri, None)
        return [self._publish(uri)]

    def _handle_did_close(self, msg, msg_id):
        uri = ((msg.get("params") or {}).get("textDocument") or {}).get("uri")
        if uri:
            self.docs.pop(uri, None)
            self.indexes.pop(uri, None)
            return [self._publish(uri, diagnostics=[])]
        return []

    # -- features -----------------------------------------------------------------

    def _handle_hover(self, msg, msg_id):
        index, pos = self._feature_target(msg)
        result = index.hover(*pos) if index else None
        return [self._ok(msg_id, result)]

    def _handle_definition(self, msg, msg_id):
        index, pos = self._feature_target(msg)
        result = index.definition(*pos) if index else None
        return [self._ok(msg_id, result)]

    def _handle_document_symbol(self, msg, msg_id):
        index, _pos = self._feature_target(msg)
        result = index.document_symbols() if index else []
        return [self._ok(msg_id, result)]

    def _handle_completion(self, msg, msg_id):
        index, _pos = self._feature_target(msg)
        result = index.completion() if index else []
        return [self._ok(msg_id, result)]

    # -- helpers --------------------------------------------------------------------

    def _feature_target(self, msg) -> Tuple[Optional[DocumentIndex],
                                            Optional[Tuple[int, int]]]:
        params = msg.get("params") or {}
        uri = (params.get("textDocument") or {}).get("uri")
        index = self._index_for(uri)
        pos = params.get("position") or {}
        if index is None:
            return None, None
        return index, (pos.get("line", 0), pos.get("character", 0))

    def _index_for(self, uri: str) -> Optional[DocumentIndex]:
        """Return (building on first use) the index for *uri*."""
        doc = self.docs.get(uri)
        if doc is None:
            return None
        index = self.indexes.get(uri)
        if index is None:
            index = DocumentIndex(doc)
            self.indexes[uri] = index
        return index

    def _publish(self, uri: str, diagnostics=None) -> Dict[str, Any]:
        if diagnostics is None:
            index = self._index_for(uri)
            diagnostics = index.diagnostics if index else []
        payload: Dict[str, Any] = {"uri": uri, "diagnostics": diagnostics}
        doc = self.docs.get(uri)
        if doc is not None and doc.version is not None:
            payload["version"] = doc.version
        return {"jsonrpc": "2.0",
                "method": "textDocument/publishDiagnostics",
                "params": payload}

    @staticmethod
    def _ok(msg_id, result) -> Dict[str, Any]:
        return {"jsonrpc": "2.0", "id": msg_id, "result": result}

    @staticmethod
    def _error(msg_id, code, message) -> Dict[str, Any]:
        return {"jsonrpc": "2.0", "id": msg_id,
                "error": {"code": code, "message": message}}

    _HANDLERS = {
        "initialize": _handle_initialize,
        "initialized": _handle_initialized,
        "textDocument/didOpen": _handle_did_open,
        "textDocument/didChange": _handle_did_change,
        "textDocument/didClose": _handle_did_close,
        "textDocument/hover": _handle_hover,
        "textDocument/definition": _handle_definition,
        "textDocument/documentSymbol": _handle_document_symbol,
        "textDocument/completion": _handle_completion,
    }