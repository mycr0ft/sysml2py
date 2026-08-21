#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AllocationUsage keeps its `allocate X to Y` connector endpoints.

Regression test for https://github.com/mycr0ft/sysmlpy/issues/5.
"""

import json

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


def test_allocate_endpoints_survive():
    raw = load_grammar_antlr("package P { part b; requirement A; allocate A to b; }")
    allocations = _find_all(raw, "AllocationUsage")
    assert len(allocations) == 1
    part = allocations[0].get("part")
    assert part is not None, "allocate endpoints were dropped"
    names = [q.get("names") for q in _find_all(part, "QualifiedName")]
    assert ["A"] in names
    assert ["b"] in names


def test_named_allocation_still_parses():
    raw = load_grammar_antlr("package P { allocation a1; }")
    allocations = _find_all(raw, "AllocationUsage")
    assert len(allocations) == 1
    assert allocations[0]["part"] is None


def test_allocate_dotted_endpoints():
    raw = load_grammar_antlr(
        "package P { part t { part array; } requirement A; allocate A to t.array; }"
    )
    allocations = _find_all(raw, "AllocationUsage")
    assert len(allocations) == 1
    assert allocations[0].get("part") is not None
    text = json.dumps(allocations[0]["part"])
    assert "array" in text
