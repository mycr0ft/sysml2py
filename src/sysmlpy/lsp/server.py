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
- ``textDocument/didOpen|didChange|didClose`` with INCREMENTAL sync
  (full-text changes without a range are still accepted), publishing
  diagnostics (syntax errors with precise ANTLR line:column ranges;
  semantic issues position-tracked to their owning declaration)
- ``textDocument/hover``          — kind/type/value summary
- ``textDocument/documentSymbol`` — hierarchical model outline
- ``textDocument/definition``     — jump to declaration
- ``textDocument/completion``     — SysML keywords + model member names,
  plus ``.``-member completion resolved through type names
- ``workspace/symbol``            — query across open documents and the
  workspace root (``*.sysml`` files under the initialized root)

Design notes
------------
* Semantic diagnostics are *position-tracked by source-order pairing*:
  the symbol walk pairs the *n*-th model element of a given
  ``(kind, name)`` with the *n*-th declaration occurrence of that pair
  in the text, so an issue's range points at its owning declaration —
  e.g. the ``part def Engine`` on line 3, not the ``engine`` usage on
  line 12.  Issues on unlocatable elements fall back to the quoted
  ``'name'``-occurrence heuristic, then to line 1.  True parser-side
  position tracking (annotating visitor dicts with token positions)
  remains future work — see docs/LSP.md for the trade-off discussion.
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

    def apply_change(self, lsp_range: Dict[str, Any], new_text: str,
                     utf16: bool = True) -> None:
        """Apply one incremental ``didChange`` content change.

        *lsp_range* is ``{"start": {"line", "character"},
        "end": {...}}`` in LSP (UTF-16 by default) coordinates;
        *new_text* replaces the range.  Positions beyond the end of the
        document are clamped.
        """
        raw = self.text.split("\n")
        si = self._pos_to_index(raw, lsp_range.get("start") or {},
                                utf16)
        ei = self._pos_to_index(raw, lsp_range.get("end") or {}, utf16)
        if ei < si:                       # degenerate range — swap
            si, ei = ei, si
        self.update(self.text[:si] + new_text + self.text[ei:])

    @staticmethod
    def _pos_to_index(raw_lines: List[str], pos: Dict[str, Any],
                      utf16: bool) -> int:
        """LSP ``{"line", "character"}`` → absolute index in ``"\n".join``."""
        line = max(0, min(int(pos.get("line", 0)), len(raw_lines) - 1))
        character = max(0, int(pos.get("character", 0)))
        text_line = raw_lines[line]
        idx = 0
        if utf16:
            units = 0
            while idx < len(text_line) and units < character:
                units += 2 if ord(text_line[idx]) > 0xFFFF else 1
                idx += 1
        else:
            idx = min(character, len(text_line))
        return sum(len(l) + 1 for l in raw_lines[:line]) + idx


# ---------------------------------------------------------------------------
# Symbol entries
# ---------------------------------------------------------------------------


class SymbolEntry:
    """A model element located in the document text."""

    __slots__ = ("name", "kind_label", "sysml_type", "is_definition",
                 "line", "start_col", "end_col", "typed_by_name",
                 "qualified", "children", "element")

    def __init__(self, name: str, kind_label: str, sysml_type: str,
                 is_definition: bool, line: int, start_col: int,
                 end_col: int, typed_by_name: Optional[str] = None,
                 element: Any = None):
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
        self.element = element


def _lsp_symbol_kind_for(sysml_type: str, is_definition: bool) -> int:
    """Map ``(sysml_type, is_definition)`` to an LSP SymbolKind."""
    t = sysml_type
    if t == "package":
        return SymbolKind.PACKAGE
    if is_definition:
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


def _lsp_symbol_kind(entry: SymbolEntry) -> int:
    """Map a sysml element to an LSP SymbolKind."""
    return _lsp_symbol_kind_for(entry.sysml_type, entry.is_definition)


# ---------------------------------------------------------------------------
# DocumentIndex — parse/analyze + text location of model elements
# ---------------------------------------------------------------------------


class DocumentIndex:
    """Parsed state of one document: model, diagnostics, symbol index.

    Built once per document version via :meth:`reparse`; diagnostics and
    all feature handlers (hover/definition/symbols/completion) read from
    this single snapshot so every feature agrees on one parse.
    """

    def __init__(self, document: Document,
                 last_good_model: Any = None):
        self.document = document
        # seed with the previous version's model so completion keeps
        # working across transiently broken states; reparse refreshes it
        self._last_good_model = last_good_model
        self.model = None
        self.diagnostics: List[Dict[str, Any]] = []
        self.symbols: List[SymbolEntry] = []
        self._by_name: Dict[str, List[SymbolEntry]] = {}
        self._child_ids: set = set()
        self._occurrence: Dict[Tuple[str, str], int] = {}
        self._element_locations: Dict[int, Tuple[int, int, int]] = {}
        self.reparse()

    # -- build ---------------------------------------------------------------

    def reparse(self) -> None:
        """Re-parse the document and rebuild diagnostics + symbols."""
        import sysmlpy

        doc = self.document
        self.symbols = []
        self._by_name = {}
        self._child_ids = set()
        self._occurrence = {}
        self._element_locations = {}
        self.diagnostics = []

        model, errors = sysmlpy.parse(doc.text)
        self.model = model
        if model is not None:
            self._last_good_model = model

        for err in errors:
            diag = self._syntax_diagnostic(err)
            if diag is not None:
                self.diagnostics.append(diag)

        if model is not None:
            # build the symbol index first: semantic issues are located
            # through the element→declaration pairing it records
            self._build_symbols()
            try:
                issues = sysmlpy.analyze(model)
            except Exception:  # analyzer must never break the editor
                issues = []
            for issue in issues:
                diag = self._semantic_diagnostic(issue)
                if diag is not None:
                    self.diagnostics.append(diag)

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
        severity = _severity_number(issue.severity)

        # Position-tracked fast path: the element's paired declaration.
        loc = self._element_locations.get(id(issue.element)) \
            if issue.element is not None else None
        if loc is None and getattr(issue, "reference", ""):
            name = issue.reference.split("::")[-1]
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

        # Heuristic fallback: names mentioned in the message text.
        candidates = re.findall(r"'([^']+)'", message)
        element_name = getattr(issue.element, "name", None)
        if element_name and element_name not in candidates:
            candidates.append(element_name)
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
        """Walk the model tree and locate each named element in the text.

        Elements are visited in source order, so the *n*-th element with
        a given ``(kind, name)`` is paired with the *n*-th declaration
        occurrence of that pair in the text (position tracking without
        parser-side line/col data).
        """
        if self.model is None:
            return

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
        key = (sysml_type, name)
        nth = self._occurrence.get(key, 0)
        self._occurrence[key] = nth + 1
        loc = self._locate_declaration(keyword, name, is_def, nth)
        if loc is None:
            return None
        line, start_col, end_col = loc
        self._element_locations[id(element)] = loc
        entry = SymbolEntry(
            name=name,
            kind_label=f"{keyword}{' def' if is_def else ''}",
            sysml_type=sysml_type,
            is_definition=is_def,
            line=line,
            start_col=start_col,
            end_col=end_col,
            typed_by_name=getattr(element, "typed_by_name", None),
            element=element,
        )
        entry.qualified = "::".join(parents + (name,))
        return entry

    def _locate_declaration(self, keyword: str, name: str,
                            is_definition: bool, nth: int = 0
                            ) -> Optional[Tuple[int, int, int]]:
        """Find the ``<keyword> [def] <name>`` declaration in the text.

        Returns ``(line, start_char, end_char)`` with *start/end* being
        Python character indices spanning the *name* token.  All
        candidate occurrences are collected in source order and the
        *nth* one is selected so repeated ``(kind, name)`` pairs map to
        their own declaration; falls back to any whole-word occurrence
        (usages, aliases, anonymous decls).
        """
        candidates = self._locate_declaration_all(keyword, name,
                                                  is_definition)
        if not candidates:
            candidates = self._locate_word_all(name)
        if not candidates:
            return None
        return candidates[nth % len(candidates)]

    def _locate_declaration_all(self, keyword: str, name: str,
                                is_definition: bool
                                ) -> List[Tuple[int, int, int]]:
        """All ``<keyword> [def] <name>`` occurrences in source order.

        For definitions, ``def``-prefixed occurrences are preferred when
        any exist (a usage and a definition sharing a name would
        otherwise collide).
        """
        pattern = re.compile(
            rf"\b{re.escape(keyword)}\s+(?:def\s+)?(?P<name>{re.escape(name)})\b"
        )
        all_occurrences: List[Tuple[int, int, int]] = []
        def_occurrences: List[Tuple[int, int, int]] = []
        for lineno, line_text in enumerate(self.document.lines):
            for m in pattern.finditer(line_text):
                loc = (lineno, m.start("name"), m.end("name"))
                all_occurrences.append(loc)
                prefix = line_text[:m.start("name")]
                if re.search(rf"\b{re.escape(keyword)}\s+def\s+$", prefix):
                    def_occurrences.append(loc)
        if is_definition and def_occurrences:
            return def_occurrences
        return all_occurrences

    def _locate_word_all(self, name: str
                         ) -> List[Tuple[int, int, int]]:
        """All whole-word occurrences of *name* in source order."""
        pattern = re.compile(rf"\b{re.escape(name)}\b")
        out = []
        for lineno, line_text in enumerate(self.document.lines):
            for m in pattern.finditer(line_text):
                out.append((lineno, _utf16_len(line_text[:m.start()]),
                            _utf16_len(line_text[:m.end()])))
        return out

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

    def completion(self, line: Optional[int] = None,
                   utf16_col: Optional[int] = None) -> List[Dict[str, Any]]:
        """Completion items: SysML keywords + every named model element.

        When *line*/*utf16_col* sit right after ``base.``, return the
        members of the resolved type of *base* instead (falling back to
        the full list when the base cannot be resolved).
        """
        if line is not None and utf16_col is not None:
            member_items = self._member_completion(line, utf16_col)
            if member_items is not None:
                return member_items
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
        if not self.symbols and self._last_good_model is not None:
            # transiently broken document: offer the last good names
            for name, st, is_def in self._lastgood_names():
                if name in seen:
                    continue
                seen.add(name)
                items.append({
                    "label": name,
                    "kind": _lsp_symbol_kind_for(st, is_def),
                    "detail": _KIND_KEYWORD.get(st, st),
                })
        return items

    def _lastgood_names(self) -> List[Tuple[str, str, bool]]:
        """(name, sysml_type, is_definition) from the last good model."""
        out: List[Tuple[str, str, bool]] = []

        def walk(el) -> None:
            for child in getattr(el, "children", []) or []:
                name = getattr(child, "name", None)
                if name:
                    out.append((name,
                                getattr(child, "sysml_type", None)
                                or "element",
                                bool(getattr(child, "is_definition",
                                             False))))
                walk(child)

        walk(self._last_good_model)
        return out

    _DOT_CONTEXT_RE = re.compile(r"([A-Za-z_]\w*)\s*\.\s*([A-Za-z_]\w*)?$")

    def _member_completion(self, line: int, utf16_col: int
                           ) -> Optional[List[Dict[str, Any]]]:
        """Member items for ``base.`` completion (or ``None`` to fall back)."""
        line_text = self.document.line_text(line)
        col = 0
        units = 0
        while col < len(line_text) and units < utf16_col:
            units += 2 if ord(line_text[col]) > 0xFFFF else 1
            col += 1
        before = line_text[:col]
        m = self._DOT_CONTEXT_RE.search(before)
        if not m:
            return None
        base, prefix = m.group(1), m.group(2) or ""
        target = self._resolve_member_base(base)
        if target is None:
            return None
        items = []
        seen = set()
        for child in getattr(target, "children", []) or []:
            name = getattr(child, "name", None)
            if not name or name in seen or not name.startswith(prefix):
                continue
            seen.add(name)
            st = getattr(child, "sysml_type", None) or "element"
            is_def = bool(getattr(child, "is_definition", False))
            detail = f"{_KIND_KEYWORD.get(st, st)}{' def' if is_def else ''}"
            typed = getattr(child, "typed_by_name", None)
            if typed:
                detail += f" : {typed}"
            items.append({
                "label": name,
                "kind": _lsp_symbol_kind_for(st, is_def),
                "detail": detail,
            })
        return items

    def _resolve_member_base(self, base: str):
        """Resolve *base* to a definition element for member completion.

        Prefers a usage named *base* typed by a definition known in this
        document, then a definition named *base* itself.  When the
        current text does not parse (half-typed expression), resolution
        falls back to the last successfully parsed model.
        """
        entries = self._by_name.get(base)
        if entries:
            for e in entries:
                if (not e.is_definition and e.typed_by_name
                        and e.element is not None):
                    short = e.typed_by_name.split("::")[-1]
                    for de in self._by_name.get(short, []):
                        if de.is_definition:
                            return de.element
            for e in entries:
                if e.is_definition:
                    return e.element
        if self._last_good_model is not None:
            return self._resolve_in_model(self._last_good_model, base)
        return None

    def _resolve_in_model(self, model, base: str):
        """Resolve *base* to a definition element by walking *model*."""
        named: List[Any] = []

        def collect(el) -> None:
            for child in getattr(el, "children", []) or []:
                if getattr(child, "name", None) == base:
                    named.append(child)
                collect(child)

        collect(model)
        for el in named:
            if (not getattr(el, "is_definition", False)
                    and getattr(el, "typed_by_name", None)):
                typed = el.typed_by_name.split("::")[-1]
                target = self._find_definition(model, typed)
                if target is not None:
                    return target
        for el in named:
            if getattr(el, "is_definition", False):
                return el
        return None

    def _find_definition(self, model, name: str):
        """Depth-first search for a definition named *name*."""
        for child in getattr(model, "children", []) or []:
            if (getattr(child, "name", None) == name
                    and getattr(child, "is_definition", False)):
                return child
            found = self._find_definition(child, name)
            if found is not None:
                return found
        return None


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
        # per-uri last successfully parsed model (survives re-indexing
        # on every keystroke) — backs completion in broken states
        self.last_good: Dict[str, Any] = {}
        self.client_capabilities: Dict[str, Any] = {}
        self.workspace_root: Optional[str] = None   # filesystem path
        self._ws_cache: Optional[List[Dict[str, Any]]] = None
        self._ws_dirty = True
        self.initialized = False
        self.shutdown_requested = False
        self.exited = False
        self.server_capabilities = {
            "positionEncoding": "utf-16",
            # INCREMENTAL (v0.83.0); full-text changes without a range
            # are still accepted for clients that stay in full mode.
            "textDocumentSync": {"openClose": True, "change": 2},
            "hoverProvider": True,
            "definitionProvider": True,
            "documentSymbolProvider": True,
            "workspaceSymbolProvider": True,
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
        root_uri = params.get("rootUri")
        if root_uri:
            self.workspace_root = self._uri_to_path(root_uri)
        folders = params.get("workspaceFolders") or []
        if self.workspace_root is None and folders:
            self.workspace_root = self._uri_to_path(
                folders[0].get("uri", "") or "")
        self._ws_dirty = True
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
        self._ws_dirty = True
        return [self._publish(uri)]

    def _handle_did_change(self, msg, msg_id):
        params = msg.get("params") or {}
        uri = (params.get("textDocument") or {}).get("uri")
        doc = self.docs.get(uri)
        if doc is None:
            return []
        td = params.get("textDocument") or {}
        changes = params.get("contentChanges") or []
        for change in changes:
            if change.get("range") is not None:
                # INCREMENTAL: range-based edit against the current text
                doc.apply_change(change["range"], change.get("text", ""))
            else:
                # range-less change = full-text replacement (spec)
                doc.update(change.get("text", doc.text))
        if td.get("version") is not None:
            doc.version = td.get("version")
        self._ws_dirty = True
        self.indexes.pop(uri, None)
        return [self._publish(uri)]

    def _handle_did_close(self, msg, msg_id):
        uri = ((msg.get("params") or {}).get("textDocument") or {}).get("uri")
        if uri:
            self.docs.pop(uri, None)
            self.indexes.pop(uri, None)
            self.last_good.pop(uri, None)
            self._ws_dirty = True
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
        index, pos = self._feature_target(msg)
        result = index.completion(*pos) if index else []
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
            index = DocumentIndex(doc, self.last_good.get(uri))
            self.indexes[uri] = index
            if index._last_good_model is not None:
                self.last_good[uri] = index._last_good_model
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

    # -- workspace/symbol ----------------------------------------------------

    def _handle_workspace_symbol(self, msg, msg_id):
        params = msg.get("params") or {}
        query = (params.get("query") or "").lower()
        return [self._ok(msg_id, self._workspace_symbols(query))]

    def _workspace_symbols(self, query: str) -> List[Dict[str, Any]]:
        """Symbols matching *query* across open docs + workspace root.

        Matching is case-insensitive substring (LSP leaves the exact
        matcher to the server); results are capped at 200.  The root
        scan caches its result until the next document change.
        """
        results: List[Dict[str, Any]] = []
        seen = set()
        for uri in list(self.docs):
            index = self._index_for(uri)
            for entry in (index.symbols if index else []):
                if query and query not in entry.name.lower():
                    continue
                key = (uri, entry.name, entry.line)
                if key in seen:
                    continue
                seen.add(key)
                results.append({
                    "name": entry.name,
                    "kind": _lsp_symbol_kind(entry),
                    "location": {
                        "uri": uri,
                        "range": {
                            "start": {"line": entry.line,
                                      "character": entry.start_col},
                            "end": {"line": entry.line,
                                    "character": entry.end_col},
                        },
                    },
                    "containerName":
                        entry.qualified.rsplit("::", 1)[0]
                        if "::" in entry.qualified else "",
                })
        open_uris = set(self.docs)
        for sym in self._workspace_file_symbols():
            if sym["location"]["uri"] in open_uris:
                continue
            if query and query not in sym["name"].lower():
                continue
            results.append(sym)
        return results[:200]

    def _workspace_file_symbols(self) -> List[Dict[str, Any]]:
        """Scan ``*.sysml`` files under the workspace root (cached)."""
        if self._ws_cache is not None and not self._ws_dirty:
            return self._ws_cache
        import sysmlpy

        out: List[Dict[str, Any]] = []
        from pathlib import Path as _Path

        for path, uri in self._workspace_files():
            try:
                model = sysmlpy.loads(
                    _Path(path).read_text(encoding="utf-8"))
            except Exception:
                continue

            def walk(el, container: str) -> None:
                for child in getattr(el, "children", []) or []:
                    name = getattr(child, "name", None)
                    if name:
                        st = getattr(child, "sysml_type", None) or "element"
                        is_def = bool(getattr(child, "is_definition", False))
                        out.append({
                            "name": name,
                            "kind": _lsp_symbol_kind_for(st, is_def),
                            "location": {
                                "uri": uri,
                                "range": {
                                    "start": {"line": 0, "character": 0},
                                    "end": {"line": 0, "character": 1},
                                },
                            },
                            "containerName": container,
                        })
                        walk(child, name)
                    else:
                        walk(child, container)

            walk(model, "")
        self._ws_cache = out
        self._ws_dirty = False
        return out

    def _workspace_files(self) -> List[Tuple[str, str]]:
        """(path, uri) for ``*.sysml`` files under the root, capped at 100."""
        root = self.workspace_root
        if not root:
            return []
        from pathlib import Path as _Path

        rootp = _Path(root)
        if not rootp.is_dir():
            return []
        skip = {".git", "__pycache__", "node_modules", ".venv"}
        out: List[Tuple[str, str]] = []
        for p in sorted(rootp.rglob("*.sysml")):
            if skip & {part.lower() for part in p.parts}:
                continue
            out.append((str(p), self._path_to_uri(p)))
            if len(out) >= 100:
                break
        return out

    @staticmethod
    def _uri_to_path(uri: str) -> Optional[str]:
        """``file:///a/b.sysml`` → ``/a/b.sysml`` (``None`` otherwise)."""
        from urllib.parse import unquote, urlparse

        if not uri:
            return None
        parsed = urlparse(uri)
        if parsed.scheme and parsed.scheme != "file":
            return None
        path = unquote(parsed.path)
        return path or None

    @staticmethod
    def _path_to_uri(path) -> str:
        from pathlib import Path as _Path
        from urllib.parse import quote

        return "file://" + quote(str(_Path(path).resolve()))

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
        "workspace/symbol": _handle_workspace_symbol,
    }