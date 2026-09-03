#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the LSP server (v0.65.0 — Adoption Roadmap Goal 5).

Covers:
- protocol framing (encode/read round-trip, split reads, malformed input)
- server lifecycle (initialize/uninitialized guard/unknown method/shutdown/exit)
- diagnostics (syntax ranges, semantic locating, change/close updates)
- features (hover, documentSymbol, definition, completion)
- stdio transport (in-memory pipe end-to-end + subprocess smoke test)
"""

import io
import json
import subprocess
import sys

import pytest

from sysmlpy.lsp import (
    Document, DocumentIndex, SysmlLanguageServer,
    encode_message, read_message, SymbolKind,
)

URI = "file:///tmp/lsp_demo.sysml"

MODEL_TEXT = """package VehicleSpec {
    part def Vehicle {
        attribute mass : Real := 1200;
        part wheels: Wheel[4];
    }
    part def Wheel {
        attribute radius : Real := 0.3 [m];
    }
}"""


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def col_of(text, needle, line=0, after=0):
    """Return the LSP character column just inside *needle* on *line*."""
    lines = text.splitlines()
    idx = lines[line].index(needle, after)
    return line, idx + 1


class Client:
    """Tiny in-memory LSP client driving SysmlLanguageServer directly."""

    def __init__(self):
        self.server = SysmlLanguageServer()
        self._next_id = 1

    def notify(self, method, params=None):
        msg = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            msg["params"] = params
        return self.server.handle_message(msg)

    def request(self, method, params=None):
        msg = {"jsonrpc": "2.0", "method": method, "id": self._next_id}
        self._next_id += 1
        if params is not None:
            msg["params"] = params
        responses = self.server.handle_message(msg)
        assert len(responses) == 1
        return responses[0]

    def initialize(self):
        resp = self.request("initialize", {"capabilities": {}})
        assert "capabilities" in resp["result"]
        self.notify("initialized")
        return resp["result"]["capabilities"]

    def open(self, text, uri=URI, version=1):
        return self.notify("textDocument/didOpen", {
            "textDocument": {"uri": uri, "text": text,
                             "version": version, "languageId": "sysml"},
        })

    def diagnostics(self):
        return self.server.indexes[URI].diagnostics


# ---------------------------------------------------------------------------
# protocol framing
# ---------------------------------------------------------------------------


class TestFraming:

    def test_round_trip(self):
        payload = {"jsonrpc": "2.0", "id": 7,
                   "method": "textDocument/hover",
                   "params": {"position": {"line": 0, "character": 3}}}
        stream = io.BytesIO(encode_message(payload))
        assert read_message(stream) == payload

    def test_two_messages_sequential(self):
        payloads = [{"jsonrpc": "2.0", "id": 1, "method": "a"},
                    {"jsonrpc": "2.0", "id": 2, "method": "b"}]
        blob = b"".join(encode_message(p) for p in payloads)
        stream = io.BytesIO(blob)
        assert read_message(stream) == payloads[0]
        assert read_message(stream) == payloads[1]

    def test_non_ascii_payload(self):
        payload = {"jsonrpc": "2.0", "id": 1, "result": "héllo ☃"}
        stream = io.BytesIO(encode_message(payload))
        assert read_message(stream) == payload

    def test_clean_eof_returns_none(self):
        assert read_message(io.BytesIO(b"")) is None

    def test_missing_content_length_raises(self):
        with pytest.raises(ValueError):
            read_message(io.BytesIO(b"Content-Type: text\r\n\r\n{}"))

    def test_short_body_raises(self):
        header = b"Content-Length: 100\r\n\r\n{"
        with pytest.raises(ValueError):
            read_message(io.BytesIO(header))


# ---------------------------------------------------------------------------
# server lifecycle
# ---------------------------------------------------------------------------


class TestLifecycle:

    def test_initialize_returns_capabilities(self):
        client = Client()
        caps = client.initialize()
        assert caps["hoverProvider"] is True
        assert caps["definitionProvider"] is True
        assert caps["documentSymbolProvider"] is True
        assert caps["textDocumentSync"]["change"] == 1  # FULL

    def test_request_before_initialize_is_rejected(self):
        client = Client()
        resp = client.request("textDocument/hover",
                              {"textDocument": {"uri": URI},
                               "position": {"line": 0, "character": 0}})
        assert resp["error"]["code"] == -32002

    def test_unknown_method_returns_error(self):
        client = Client()
        client.initialize()
        resp = client.request("nope/nothing")
        assert resp["error"]["code"] == -32601

    def test_unknown_notification_ignored(self):
        client = Client()
        client.initialize()
        assert client.notify("$/cancelRequest", {"id": 1}) == []

    def test_shutdown_then_invalid_request(self):
        client = Client()
        client.initialize()
        resp = client.request("shutdown")
        assert resp["result"] is None
        resp = client.request("textDocument/hover",
                              {"textDocument": {"uri": URI},
                               "position": {"line": 0, "character": 0}})
        assert resp["error"]["code"] == -32600

    def test_exit_sets_flag(self):
        client = Client()
        client.initialize()
        client.notify("exit")
        assert client.server.exited is True

    def test_response_to_server_request_ignored(self):
        client = Client()
        assert client.server.handle_message({"jsonrpc": "2.0", "id": 1,
                                             "result": None}) == []

    def test_request_without_open_document(self):
        client = Client()
        client.initialize()
        resp = client.request("textDocument/hover",
                              {"textDocument": {"uri": URI},
                               "position": {"line": 0, "character": 0}})
        assert resp["result"] is None


# ---------------------------------------------------------------------------
# diagnostics
# ---------------------------------------------------------------------------


class TestDiagnostics:

    def test_clean_model_only_library_warnings(self):
        client = Client()
        client.initialize()
        client.open(MODEL_TEXT)
        diags = client.diagnostics()
        # IMPLICIT_LIBRARY_IMPORT warnings are expected (no explicit imports)
        codes = {d["code"] for d in diags}
        assert "syntax" not in codes
        assert all(d["severity"] == 2 for d in diags if
                   d["code"] == "IMPLICIT_LIBRARY_IMPORT")

    def test_syntax_error_range(self):
        client = Client()
        client.initialize()
        client.open("package P {\n  part def Broken {\n    attribute x :=\n}\n")
        syntax = [d for d in client.diagnostics() if d["code"] == "syntax"]
        assert syntax, "expected a syntax diagnostic"
        d = syntax[0]
        assert d["range"]["start"]["line"] >= 1
        assert d["severity"] == 1
        assert d["source"] == "sysmlpy"

    def test_semantic_error_located_in_text(self):
        text = ("package P {\n"
                "    part def V { attribute a : Real := 1; }\n"
                "    attribute b : Boolean := a > missing;\n"
                "}\n")
        client = Client()
        client.initialize()
        client.open(text)
        errs = [d for d in client.diagnostics()
                if d["severity"] == 1 and d["code"] != "syntax"]
        assert errs
        # the unresolved 'missing' should highlight the name on line 2
        target = [d for d in errs if "missing" in d["message"]]
        assert target
        assert target[0]["range"]["start"]["line"] == 2

    def test_did_change_revalidates(self):
        client = Client()
        client.initialize()
        client.open("package P { part def V; }", version=1)
        before = len(client.diagnostics())
        client.notify("textDocument/didChange", {
            "textDocument": {"uri": URI, "version": 2},
            "contentChanges": [{"text":
                                "package P {\n  part def V {\n    oops\n}\n"}],
        })
        after = client.diagnostics()
        assert any(d["code"] == "syntax" for d in after)

    def test_did_close_clears_diagnostics(self):
        client = Client()
        client.initialize()
        client.open(MODEL_TEXT)
        pubs = client.notify("textDocument/didClose",
                             {"textDocument": {"uri": URI}})
        assert pubs and pubs[0]["method"] == "textDocument/publishDiagnostics"
        assert pubs[0]["params"]["diagnostics"] == []
        assert URI not in client.server.docs

    def test_unparsable_document_still_publishes(self):
        client = Client()
        client.initialize()
        client.open("package P { part def Broken {")
        syntax = [d for d in client.diagnostics() if d["code"] == "syntax"]
        assert syntax


# ---------------------------------------------------------------------------
# hover / definition / documentSymbol / completion
# ---------------------------------------------------------------------------


class TestHover:

    def test_hover_definition(self):
        client = Client()
        client.initialize()
        client.open(MODEL_TEXT)
        line, ch = col_of(MODEL_TEXT, "Vehicle", line=1)
        resp = client.request("textDocument/hover",
                              {"textDocument": {"uri": URI},
                               "position": {"line": line, "character": ch}})
        hover = resp["result"]
        assert hover is not None
        value = hover["contents"]["value"]
        assert "part def" in value
        assert "`Vehicle`" in value
        assert "VehicleSpec::Vehicle" in hover["contents"]["value"]

    def test_hover_attribute_shows_type_and_value(self):
        client = Client()
        client.initialize()
        client.open(MODEL_TEXT)
        line, ch = col_of(MODEL_TEXT, "mass", line=2)
        resp = client.request("textDocument/hover",
                              {"textDocument": {"uri": URI},
                               "position": {"line": line, "character": ch}})
        value = resp["result"]["contents"]["value"]
        assert "`mass`" in value
        assert "Real" in value
        assert "1200" in value

    def test_hover_whitespace_returns_none(self):
        client = Client()
        client.initialize()
        client.open(MODEL_TEXT)
        resp = client.request("textDocument/hover",
                              {"textDocument": {"uri": URI},
                               "position": {"line": 0, "character": 0}})
        assert resp["result"] is None

    def test_hover_unknown_name_returns_none(self):
        client = Client()
        client.initialize()
        client.open(MODEL_TEXT)
        resp = client.request("textDocument/hover",
                              {"textDocument": {"uri": URI},
                               "position": {"line": 2,
                                            "character": 200}})
        assert resp["result"] is None


class TestDefinition:

    def test_usage_declaration_is_self(self):
        client = Client()
        client.initialize()
        client.open(MODEL_TEXT)
        # hovering the usage name 'wheels' jumps to its own declaration
        line, ch = col_of(MODEL_TEXT, "wheels", line=3)
        resp = client.request("textDocument/definition",
                              {"textDocument": {"uri": URI},
                               "position": {"line": line, "character": ch}})
        loc = resp["result"]
        assert loc is not None
        assert loc["range"]["start"]["line"] == 3

    def test_type_name_jumps_to_type_declaration(self):
        client = Client()
        client.initialize()
        client.open(MODEL_TEXT)
        # hovering the type name 'Wheel' (in 'wheels: Wheel[4]') jumps to
        # its 'part def Wheel' declaration on line 5
        line, ch = col_of(MODEL_TEXT, "Wheel[4]", line=3)
        resp = client.request("textDocument/definition",
                              {"textDocument": {"uri": URI},
                               "position": {"line": line, "character": ch}})
        loc = resp["result"]
        assert loc is not None
        assert loc["range"]["start"]["line"] == 5

    def test_definition_on_declaration_is_self(self):
        client = Client()
        client.initialize()
        client.open(MODEL_TEXT)
        line, ch = col_of(MODEL_TEXT, "Vehicle", line=1)
        resp = client.request("textDocument/definition",
                              {"textDocument": {"uri": URI},
                               "position": {"line": line, "character": ch}})
        loc = resp["result"]
        assert loc is not None
        assert loc["range"]["start"]["line"] == 1


class TestDocumentSymbol:

    def test_hierarchical_outline(self):
        client = Client()
        client.initialize()
        client.open(MODEL_TEXT)
        symbols = client.request("textDocument/documentSymbol",
                                 {"textDocument": {"uri": URI}})["result"]
        names = [s["name"] for s in symbols]
        assert "VehicleSpec" in names
        pkg = symbols[0]
        assert pkg["kind"] == SymbolKind.PACKAGE
        child_names = [c["name"] for c in pkg["children"]]
        assert "Vehicle" in child_names and "Wheel" in child_names
        vehicle = next(c for c in pkg["children"] if c["name"] == "Vehicle")
        vattrs = [c["name"] for c in vehicle["children"]]
        assert "mass" in vattrs and "wheels" in vattrs
        # definition detail carries the def marker
        assert "def" in vehicle["detail"]

    def test_symbol_kinds(self):
        client = Client()
        client.initialize()
        client.open(MODEL_TEXT)
        symbols = client.request("textDocument/documentSymbol",
                                 {"textDocument": {"uri": URI}})["result"]
        pkg = symbols[0]
        vehicle = next(c for c in pkg["children"] if c["name"] == "Vehicle")
        assert vehicle["kind"] == SymbolKind.CLASS
        mass = next(c for c in vehicle["children"] if c["name"] == "mass")
        assert mass["kind"] == SymbolKind.FIELD


class TestCompletion:

    def test_keywords_and_members(self):
        client = Client()
        client.initialize()
        client.open(MODEL_TEXT)
        resp = client.request("textDocument/completion",
                              {"textDocument": {"uri": URI},
                               "position": {"line": 0, "character": 0}})
        labels = [i["label"] for i in resp["result"]]
        assert "package" in labels and "part" in labels
        assert "Vehicle" in labels and "radius" in labels

    def test_keyword_items_are_marked(self):
        client = Client()
        client.initialize()
        client.open(MODEL_TEXT)
        resp = client.request("textDocument/completion",
                              {"textDocument": {"uri": URI},
                               "position": {"line": 0, "character": 0}})
        kw = next(i for i in resp["result"] if i["label"] == "package")
        assert kw["kind"] == 14  # Keyword


# ---------------------------------------------------------------------------
# stdio transport (in-memory)
# ---------------------------------------------------------------------------


def framed(msgs):
    return b"".join(encode_message(m) for m in msgs)


class TestStdioServe:

    def _serve(self, incoming: bytes):
        inp = io.BytesIO(framed(msgs))
        out = io.BytesIO()
        serve = sys.modules["sysmlpy.lsp.stdio"].serve
        serve(inp, out)
        out.seek(0)
        responses = []
        while True:
            try:
                msg = read_message(out)
            except (ValueError, EOFError):
                break
            if msg is None:
                break
            responses.append(msg)
        return responses

    def test_full_session_over_pipe(self):
        msgs = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize",
             "params": {"capabilities": {}}},
            {"jsonrpc": "2.0", "method": "initialized", "params": {}},
            {"jsonrpc": "2.0", "method": "textDocument/didOpen",
             "params": {"textDocument": {"uri": URI, "text": MODEL_TEXT,
                                         "version": 1}}},
            {"jsonrpc": "2.0", "id": 2, "method": "textDocument/hover",
             "params": {"textDocument": {"uri": URI},
                        "position": dict(zip(("line", "character"),
                                             col_of(MODEL_TEXT, "mass",
                                                    line=2)))}},
            {"jsonrpc": "2.0", "id": 3, "method": "shutdown"},
            {"jsonrpc": "2.0", "method": "exit"},
        ]
        responses = self._run(msgs)
        by_id = {r.get("id"): r for r in responses if "id" in r}
        assert by_id[1]["result"]["capabilities"]["hoverProvider"] is True
        assert "mass" in by_id[2]["result"]["contents"]["value"]
        assert any(r.get("method") == "textDocument/publishDiagnostics"
                   for r in responses)
        # EOF after exit — loop terminated cleanly

    def _run(self, msgs):
        inp = io.BytesIO(framed(msgs))
        out = io.BytesIO()
        from sysmlpy.lsp.stdio import serve
        serve(inp, out)
        out.seek(0)
        responses = []
        while True:
            try:
                msg = read_message(out)
            except (ValueError, EOFError):
                break
            if msg is None:
                break
            responses.append(msg)
        return responses


# ---------------------------------------------------------------------------
# subprocess smoke test: python -m sysmlpy.lsp
# ---------------------------------------------------------------------------


class TestSubprocess:

    def test_python_m_sysmlpy_lsp(self):
        """Drive the real stdio server end-to-end in a subprocess."""
        msgs = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize",
             "params": {"capabilities": {}}},
            {"jsonrpc": "2.0", "method": "initialized", "params": {}},
            {"jsonrpc": "2.0", "method": "textDocument/didOpen",
             "params": {"textDocument": {"uri": URI, "text": MODEL_TEXT,
                                         "version": 1}}},
            {"jsonrpc": "2.0", "id": 2, "method": "shutdown"},
            {"jsonrpc": "2.0", "method": "exit"},
        ]
        blob = b"".join(encode_message(m) for m in msgs)
        proc = subprocess.run(
            [sys.executable, "-m", "sysmlpy.lsp"],
            input=blob, capture_output=True, timeout=120,
        )
        assert proc.returncode == 0, proc.stderr.decode()[-500:]
        stream = io.BytesIO(proc.stdout)
        results = {}
        while True:
            try:
                msg = read_message(stream)
            except (ValueError, EOFError):
                break
            if msg is None:
                break
            if "id" in msg:
                results[msg["id"]] = msg
        assert results[1]["result"]["capabilities"][
            "documentSymbolProvider"] is True

    def test_version_flag(self):
        proc = subprocess.run(
            [sys.executable, "-m", "sysmlpy.lsp", "--version"],
            capture_output=True, text=True, timeout=60,
        )
        assert proc.returncode == 0
        assert proc.stdout.strip()


# ---------------------------------------------------------------------------
# DocumentIndex unit-level behavior
# ---------------------------------------------------------------------------


class TestDocumentIndex:

    def test_index_builds_from_document(self):
        doc = Document(URI, MODEL_TEXT)
        index = DocumentIndex(doc)
        assert index.model is not None
        assert any(e.name == "Vehicle" for e in index.symbols)

    def test_symbol_qualified_names(self):
        doc = Document(URI, MODEL_TEXT)
        index = DocumentIndex(doc)
        mass = next(e for e in index.symbols if e.name == "mass")
        assert mass.qualified == "VehicleSpec::Vehicle::mass"

    def test_reparse_after_text_change(self):
        doc = Document(URI, "package P { part def V; }")
        index = DocumentIndex(doc)
        assert index.symbols
        doc.update("package P {\n  part def V {\n    oops\n}\n")
        index.reparse()
        assert any(d["code"] == "syntax" for d in index.diagnostics)