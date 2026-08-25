#!/usr/bin/env python3
"""Partial-parse recovery: ``loads_partial`` / ``load_partial`` return
partial data when the input has syntax errors, rather than raising
:class:`SysMLSyntaxError`.

The canonical broken input is ``validation/valid/Import_Visibility_Valid.sysml``
— its XPECT header expects a parse error on the visibility-less
``import ScalarValues;``, which the sysmlpy grammar legitimately rejects.
The empty ``.error`` sidecar per this repo's convention means the loader
should still produce a useful partial result rather than blow up.
"""

import pytest

from sysmlpy import (
    PartialParseError,
    SysMLSyntaxError,
    load,
    load_partial,
    loads,
    loads_partial,
)
from sysmlpy.formatting import classtree


BROKEN_PATH = "tests/sysmlv2/validation/valid/Import_Visibility_Valid.sysml"


def _broken_text():
    with open(BROKEN_PATH) as f:
        return f.read()


def test_loads_partial_clean_returns_dict():
    """On well-formed input, ``loads_partial`` behaves like ``loads``."""
    text = "package P { part def V; }"
    result = loads_partial(text)
    assert isinstance(result, dict)
    assert result["name"] == "PackageBodyElement"


def test_strict_load_still_raises_on_broken_input():
    """The strict entry points are unchanged: still raise on errors."""
    with pytest.raises(SysMLSyntaxError):
        loads(_broken_text())


def test_loads_partial_raises_partial_parse_error():
    text = _broken_text()
    with pytest.raises(PartialParseError) as excinfo:
        loads_partial(text)
    err = excinfo.value
    assert len(err.errors) >= 1
    assert err.partial is not None
    assert err.source == text


def test_load_partial_raises_partial_parse_error_with_model_dumpable():
    """``load_partial``'s exception carries a partial visitor dict that
    is round-trippable through ``classtree`` / ``dump``."""
    with pytest.raises(PartialParseError) as excinfo:
        load_partial(_broken_text())
    err = excinfo.value
    assert err.partial is not None
    model = classtree(err.partial)
    dump = model.dump()
    # The three valid imports survive; the broken one is dropped.
    assert "public import ScalarValues;" in dump
    assert "private import ScalarValues;" in dump
    assert "protected import ScalarValues;" in dump
    assert dump.count("import") == 3


def test_partial_parse_error_fields_are_well_typed():
    err = PartialParseError(errors=["x"], partial={"a": 1}, source="...")
    assert err.errors == ["x"]
    assert err.partial == {"a": 1}
    assert err.source == "..."
    assert isinstance(str(err), str)


def test_load_partial_clean_returns_model():
    """On well-formed input, ``load_partial`` behaves like ``load``."""
    text = "package P { part def V; }"
    m = load_partial(text)
    dump = m.dump()
    assert "package P" in dump
    assert "part def V" in dump