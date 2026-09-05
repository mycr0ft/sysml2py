#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch 4 LSP tests (v0.83.0).

Covers:
- incremental text sync (ranged insert/delete/replace, clamping, UTF-16)
- position-tracked semantic diagnostics (source-order pairing)
- workspace/symbol (open docs + workspace root scan, cache invalidation)
- ``.``-member completion resolved through type names
"""

import pytest

from sysmlpy.lsp import (
    Document, DocumentIndex, SysmlLanguageServer, SymbolKind,
)

URI = "file:///tmp/lsp_demo.sysml"


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

    def initialize(self, root=None):
        params = {"capabilities": {}}
        if root is not None:
            params["rootUri"] = "file://" + str(root)
        resp = self.request("initialize", params)
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
# incremental sync
# ---------------------------------------------------------------------------


class TestIncrementalSync:

    def _open(self, text, version=1):
        client = Client()
        client.initialize()
        client.open(text, version=version)
        return client

    @staticmethod
    def server_text(client):
        return client.server.docs[URI].text

    def _change(self, client, version, *changes):
        client.notify("textDocument/didChange", {
            "textDocument": {"uri": URI, "version": version},
            "contentChanges": list(changes),
        })

    def test_change_capability_is_incremental(self):
        caps = Client().initialize()
        assert caps["textDocumentSync"]["change"] == 2

    def test_range_insert(self):
        text = "package P { part def V; }"
        client = self._open(text)
        self._change(client, 2, {
            "range": {"start": {"line": 0, "character": 21},
                      "end": {"line": 0, "character": 23}},
            "text": "Vehicle;",
        })
        assert self.server_text(client) == "package P { part def Vehicle; }"
        assert not [d for d in client.diagnostics()
                    if d["code"] == "syntax"]

    def test_range_delete(self):
        client = self._open("package P { part def Vehicle; }")
        self._change(client, 2, {
            "range": {"start": {"line": 0, "character": 21},
                      "end": {"line": 0, "character": 28}},
            "text": "",
        })
        assert self.server_text(client) == "package P { part def ; }"

    def test_range_replace(self):
        client = self._open("package P { part def Vehicle; }")
        self._change(client, 2, {
            "range": {"start": {"line": 0, "character": 21},
                      "end": {"line": 0, "character": 28}},
            "text": "Bike",
        })
        assert self.server_text(client) == "package P { part def Bike; }"

    def test_multiline_range_replace(self):
        text = "package P {\n  part def A;\n  part def B;\n}"
        client = self._open(text)
        self._change(client, 2, {
            "range": {"start": {"line": 1, "character": 2},
                      "end": {"line": 2, "character": 13}},
            "text": "part def C;",
        })
        assert self.server_text(client) == "package P {\n  part def C;\n}"

    def test_full_change_without_range_still_works(self):
        client = self._open("package P { part def A; }")
        client.notify("textDocument/didChange", {
            "textDocument": {"uri": URI, "version": 2},
            "contentChanges": [{"text": "package P { part def B; }"}],
        })
        assert self.server_text(client) == "package P { part def B; }"

    def test_mixed_full_then_incremental(self):
        client = self._open("package P { part def A; }")
        self._change(client, 2,
                     {"text": "package P { part def AB; }"},
                     {"range": {"start": {"line": 0, "character": 23},
                                "end": {"line": 0, "character": 23}},
                      "text": "X"})
        assert self.server_text(client) == "package P { part def ABX; }"

    def test_sequential_incremental_edits(self):
        client = self._open("package P { part def A; }")
        self._change(client, 2, {
            "range": {"start": {"line": 0, "character": 21},
                      "end": {"line": 0, "character": 22}},
            "text": "B"})
        self._change(client, 3, {
            "range": {"start": {"line": 0, "character": 22},
                      "end": {"line": 0, "character": 22}},
            "text": "C"})
        assert self.server_text(client) == "package P { part def BC; }"

    def test_version_tracked_through_incremental(self):
        client = self._open("package P { part def A; }", version=1)
        self._change(client, 7, {
            "range": {"start": {"line": 0, "character": 21},
                      "end": {"line": 0, "character": 22}},
            "text": "B"})
        assert client.server.docs[URI].version == 7

    def test_positions_clamped_beyond_eof(self):
        client = self._open("package P { part def A; }")
        self._change(client, 3, {
            "range": {"start": {"line": 99, "character": 0},
                      "end": {"line": 99, "character": 5}},
            "text": "X"})
        # line 99 clamps to the (single) last line of the document
        assert self.server_text(client) == "Xge P { part def A; }"

    def test_negative_line_clamped(self):
        client = self._open("package P { part def A; }")
        self._change(client, 3, {
            "range": {"start": {"line": -4, "character": 0},
                      "end": {"line": -4, "character": 0}},
            "text": "Z"})
        assert self.server_text(client).startswith("Zpackage")

    def test_utf16_column_after_astral_char(self):
        text = "package P { // \U0001F680\npart def A; }"
        client = self._open(text)
        # line 1: 'part def A; }' — insert 'B' after 'A' (col 9)
        self._change(client, 2, {
            "range": {"start": {"line": 1, "character": 10},
                      "end": {"line": 1, "character": 10}},
            "text": "B"})
        assert "part def AB" in self.server_text(client)

    def test_document_apply_change_direct(self):
        doc = Document(URI, "hello\nworld")
        doc.apply_change({"start": {"line": 1, "character": 0},
                          "end": {"line": 1, "character": 5}}, "there")
        assert doc.text == "hello\nthere"
        # UTF-16: an astral char counts as 2 units
        doc2 = Document(URI, "a\U0001F680bc")
        doc2.apply_change({"start": {"line": 0, "character": 3},
                           "end": {"line": 0, "character": 5}}, "X")
        assert doc2.text == "a\U0001F680X"


# ---------------------------------------------------------------------------
# position-tracked diagnostics (source-order pairing)
# ---------------------------------------------------------------------------


class TestPositionTracking:

    DUP_TEXT = (
        "package P {\n"
        "    part def Engine {\n"
        "        attribute speed : Real;\n"
        "    }\n"
        "    part def Engine {\n"
        "        attribute weight : Real = nope;\n"
        "    }\n"
        "}\n")

    def test_issue_on_second_duplicate_points_at_second(self):
        client = Client()
        client.initialize()
        client.open(self.DUP_TEXT)
        errs = [d for d in client.diagnostics()
                if d["severity"] == 1 and d["code"] != "syntax"]
        assert errs
        # must sit in the SECOND Engine block (line 5..6), never on the
        # first 'Engine' text hit (line 1) that the old heuristic used
        assert errs[0]["range"]["start"]["line"] >= 5

    def test_nth_occurrence_pairing(self):
        doc = Document(URI, "package P {\n  part def A;\n  part def A;\n}")
        index = DocumentIndex(doc)
        pairs = [(e.name, e.line) for e in index.symbols if e.name == "A"]
        assert pairs == [("A", 1), ("A", 2)]

    def test_element_locations_recorded(self):
        doc = Document(URI, self.DUP_TEXT)
        index = DocumentIndex(doc)
        engs = [e for e in index.symbols if e.name == "Engine"]
        assert len(engs) == 2
        assert engs[0].line == 1 and engs[1].line == 4
        for e in engs:
            assert e.element is not None
            assert index._element_locations[id(e.element)] == (
                e.line, e.start_col, e.end_col)

    def test_reference_fallback_locates_reference_name(self):
        doc = Document(URI, "package P { attribute a : Missing; }")
        index = DocumentIndex(doc)
        from sysmlpy.semantic import SemanticIssue
        issue = SemanticIssue(severity="warning", code="X",
                              message="thing", element=None,
                              reference="Missing")
        diag = index._semantic_diagnostic(issue)
        assert diag["range"]["start"]["line"] == 0
        assert diag["message"] == "thing"

    def test_unlocatable_issue_falls_back_to_zero_range(self):
        doc = Document(URI, "package P { part def A; }")
        index = DocumentIndex(doc)
        from sysmlpy.semantic import SemanticIssue
        issue = SemanticIssue(severity="warning", code="X",
                              message="zzz", element=None, reference="")
        diag = index._semantic_diagnostic(issue)
        assert diag["range"]["start"]["line"] == 0

    def test_semantic_still_publishes_after_reorder(self):
        # reparse now builds symbols BEFORE analyzing; ensure the
        # diagnostics list is still populated
        client = Client()
        client.initialize()
        client.open(self.DUP_TEXT)
        diags = client.diagnostics()
        assert any(d["severity"] == 1 and d["code"] != "syntax"
                   for d in diags)


# ---------------------------------------------------------------------------
# workspace/symbol
# ---------------------------------------------------------------------------


class TestWorkspaceSymbol:

    def test_query_over_open_documents(self):
        text = "package P {\n  part def Vehicle;\n  part def Wheel;\n}"
        client = Client()
        client.initialize()
        client.open(text)
        syms = client.request("workspace/symbol",
                              {"query": "Vehicle"})["result"]
        assert {s["name"] for s in syms} == {"Vehicle"}
        loc = syms[0]["location"]
        assert loc["uri"] == URI
        assert loc["range"]["start"]["line"] == 1

    def test_query_case_insensitive_substring(self):
        text = "package P {\n  part def Vehicle;\n}"
        client = Client()
        client.initialize()
        client.open(text)
        syms = client.request("workspace/symbol",
                              {"query": "veh"})["result"]
        assert {s["name"] for s in syms} == {"Vehicle"}

    def test_empty_query_returns_all(self):
        text = "package P {\n  part def A;\n  part def B;\n}"
        client = Client()
        client.initialize()
        client.open(text)
        syms = client.request("workspace/symbol", {"query": ""})["result"]
        assert {s["name"] for s in syms} == {"P", "A", "B"}

    def test_scan_of_workspace_root(self, tmp_path):
        (tmp_path / "a.sysml").write_text(
            "package Lib { part def Pump; }")
        (tmp_path / "sub").mkdir()
        (tmp_path / "sub" / "b.sysml").write_text(
            "package More { item Tank; }")
        (tmp_path / "notes.txt").write_text("not sysml")
        client = Client()
        client.initialize(root=tmp_path)
        syms = client.request("workspace/symbol", {"query": ""})["result"]
        names = {s["name"] for s in syms}
        assert {"Pump", "Tank"} <= names
        uris = {s["location"]["uri"] for s in syms}
        assert any(u.endswith("a.sysml") for u in uris)
        assert any(u.endswith("b.sysml") for u in uris)

    def test_open_document_not_duplicated_by_root_scan(self, tmp_path):
        (tmp_path / "open.sysml").write_text(
            "package W { part def Alpha; }")
        client = Client()
        client.initialize(root=tmp_path)
        client.open("package W { part def Alpha; }",
                    uri="file://" + str(tmp_path / "open.sysml"))
        syms = client.request("workspace/symbol",
                              {"query": "Alpha"})["result"]
        assert len(syms) == 1

    def test_cache_refreshed_after_change(self, tmp_path):
        (tmp_path / "a.sysml").write_text(
            "package Lib { part def Pump; }")
        client = Client()
        client.initialize(root=tmp_path)
        syms = client.request("workspace/symbol", {"query": ""})["result"]
        assert "Pump" in {s["name"] for s in syms}
        (tmp_path / "a.sysml").write_text(
            "package Lib { part def Valve; }")
        client.open("package Lib { part def Zed; }",
                    uri="file:///tmp/other.sysml")
        syms = client.request("workspace/symbol", {"query": ""})["result"]
        names = {s["name"] for s in syms}
        assert "Valve" in names
        assert "Zed" in names
        assert "Pump" not in names   # stale cache was invalidated

    def test_no_root_and_no_docs_gives_empty(self):
        client = Client()
        client.initialize()
        assert client.request("workspace/symbol",
                              {"query": "x"})["result"] == []

    def test_unparsable_root_file_skipped(self, tmp_path):
        (tmp_path / "bad.sysml").write_text("package Broken {")
        (tmp_path / "good.sysml").write_text(
            "package OK { part def P; }")
        client = Client()
        client.initialize(root=tmp_path)
        syms = client.request("workspace/symbol", {"query": ""})["result"]
        assert {s["name"] for s in syms} == {"OK", "P"}

    def test_container_name_carry(self):
        text = "package P {\n  part def V {\n    attribute mass : Real;\n  }\n}"
        client = Client()
        client.initialize()
        client.open(text)
        syms = client.request("workspace/symbol",
                              {"query": "mass"})["result"]
        assert len(syms) == 1
        assert syms[0]["containerName"] == "P::V"


# ---------------------------------------------------------------------------
# `.`-member completion
# ---------------------------------------------------------------------------


class TestMemberCompletion:
    """``base.`` member completion.

    The realistic editor flow is exercised: the document parses, the
    user types ``base.`` (making the text transiently unparsable), and
    completion resolves members through the last good parse.
    """

    def _req(self, good, broken, line, needle):
        client = Client()
        client.initialize()
        client.open(good)
        # simulate typing that breaks the expression
        client.notify("textDocument/didChange", {
            "textDocument": {"uri": URI, "version": 2},
            "contentChanges": [{"text": broken}]})
        lines = broken.splitlines()
        ch = lines[line].index(needle) + len(needle)
        resp = client.request("textDocument/completion",
                              {"textDocument": {"uri": URI},
                               "position": {"line": line, "character": ch}})
        return resp["result"]

    def test_member_completion_through_typed_part(self):
        good = ("package F {\n"
                "    part def Engine { attribute rpm : Real; }\n"
                "    part def Vehicle { part engine : Engine; }\n"
                "    part myCar : Vehicle;\n"
                "    attribute x : Real = myCar;\n"
                "}\n")
        broken = good.replace("myCar;", "myCar.")
        items = self._req(good, broken, 4, "myCar.")
        labels = [i["label"] for i in items]
        # myCar is typed by Vehicle → its direct members
        assert "engine" in labels

    def test_member_completion_prefix_filter(self):
        good = ("package F {\n"
                "    part def Engine {\n"
                "        attribute rpm : Real;\n"
                "        attribute temp : Real;\n"
                "    }\n"
                "    part def Vehicle { part e : Engine; }\n"
                "    part myCar : Vehicle;\n"
                "    attribute y : Real = e.r;\n"
                "}\n")
        broken = good.replace("e.r;", "e.r")
        items = self._req(good, broken, 7, "e.r")
        labels = [i["label"] for i in items]
        assert labels == ["rpm"]

    def test_definition_member_completion(self):
        good = ("package F {\n"
                "    part def Engine { attribute rpm : Real; }\n"
                "    part def Vehicle { part engine : Engine; }\n"
                "    attribute z : Real = Engine;\n"
                "}\n")
        broken = good.replace("Engine;", "Engine.")
        items = self._req(good, broken, 3, "Engine.")
        labels = [i["label"] for i in items]
        assert "rpm" in labels

    def test_unresolvable_base_falls_back_to_full_list(self):
        good = ("package F {\n"
                "    part def Engine { attribute rpm : Real; }\n"
                "    attribute q : Real = ScalarValues::Real;\n"
                "}\n")
        broken = good.replace("ScalarValues::Real;", "ScalarValues.")
        items = self._req(good, broken, 2, "ScalarValues.")
        labels = [i["label"] for i in items]
        assert "package" in labels   # keyword fallback
        assert "Engine" in labels

    def test_no_dot_context_returns_full_list(self):
        # a fully valid document, cursor not after a dot
        text = ("package F {\n"
                "    part def Engine { attribute rpm : Real; }\n"
                "    part def Vehicle { part engine : Engine; }\n"
                "}\n")
        client = Client()
        client.initialize()
        client.open(text)
        ch = text.splitlines()[1].index("def")
        resp = client.request("textDocument/completion",
                              {"textDocument": {"uri": URI},
                               "position": {"line": 1, "character": ch}})
        labels = [i["label"] for i in resp["result"]]
        assert "part" in labels and "Engine" in labels

    def test_member_items_carry_kind_and_detail(self):
        good = ("package F {\n"
                "    part def Engine { attribute rpm : Real; }\n"
                "    part def Vehicle { part engine : Engine; }\n"
                "    attribute z : Real = Engine;\n"
                "}\n")
        broken = good.replace("Engine;", "Engine.")
        items = self._req(good, broken, 3, "Engine.")
        rpm = next(i for i in items if i["label"] == "rpm")
        assert rpm["kind"] == SymbolKind.FIELD
        assert "attribute" in rpm["detail"]

    def test_outline_degrades_but_completion_survives(self):
        # while broken, the outline is empty but member completion works
        good = ("package F {\n"
                "    part def Engine { attribute rpm : Real; }\n"
                "    attribute z : Real = Engine;\n"
                "}\n")
        broken = good.replace("Engine;", "Engine.")
        client = Client()
        client.initialize()
        client.open(good)
        assert client.server.indexes[URI].symbols
        client.notify("textDocument/didChange", {
            "textDocument": {"uri": URI, "version": 2},
            "contentChanges": [{"text": broken}]})
        assert client.server.indexes[URI].symbols == []
        ch = broken.splitlines()[2].index("Engine.") + len("Engine.")
        resp = client.request("textDocument/completion",
                              {"textDocument": {"uri": URI},
                               "position": {"line": 2, "character": ch}})
        assert "rpm" in [i["label"] for i in resp["result"]]

    def test_completion_backward_compatible_no_position(self):
        doc = Document(URI, "package P { part def A; }")
        index = DocumentIndex(doc)
        items = index.completion()
        labels = [i["label"] for i in items]
        assert "package" in labels and "A" in labels