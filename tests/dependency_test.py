#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dependency statements reach parse_to_dict output.

Regression test for https://github.com/mycr0ft/sysmlpy/issues/4.
"""

from sysmlpy import load_grammar_antlr


def _find_all(node, name, out=None):
    if out is None:
        out = []
    if isinstance(node, dict):
        if node.get("name") == name:
            out.append(node)
        for value in node.values():
            _find_all(value, name, out)
    elif isinstance(node, list):
        for item in node:
            _find_all(item, name, out)
    return out


def test_bare_dependency_survives():
    raw = load_grammar_antlr("package P { part b; requirement A; dependency b to A; }")
    (dep,) = _find_all(raw, "Dependency")
    assert [q["names"] for q in dep["client"]] == [["b"]]
    assert [q["names"] for q in dep["supplier"]] == [["A"]]


def test_named_dependency_with_multiple_clients():
    raw = load_grammar_antlr(
        "package P { dependency Use from Client1, Client2 to Supplier1; }"
    )
    (dep,) = _find_all(raw, "Dependency")
    assert dep["identification"]["declaredName"] == "Use"
    assert [q["names"] for q in dep["client"]] == [["Client1"], ["Client2"]]
    assert [q["names"] for q in dep["supplier"]] == [["Supplier1"]]


def test_qualified_endpoints_split():
    raw = load_grammar_antlr(
        "package P { dependency Sub::Client to Other::Supplier; }"
    )
    (dep,) = _find_all(raw, "Dependency")
    assert [q["names"] for q in dep["client"]] == [["Sub", "Client"]]
    assert [q["names"] for q in dep["supplier"]] == [["Other", "Supplier"]]
