#!/usr/bin/env python3
"""Regression coverage for the ``redefined_name`` / ``display_name``
helpers added so callers can recover the user-visible identifier on a
Usage whose name lives only in the re-declaration grammar (``:>>``,
``:>``, ``::>``) rather than on the feature identification.

The motivating case came from a user who observed:

    attribute :>> exampleAttribute = "Example Value";

…would dump the name correctly but ``attribute.name`` returned a UUID
sentinel. The helpers expose the resolved name without changing the
historical ``self.name`` semantics (which the codebase already treats
as anonymous when it is a UUID).
"""

import pytest

from sysmlpy import loads


DEFINITION = """package DummyDefinitionModel {
    abstract view def ViewDefinition {
        attribute exampleAttribute {
            doc /* This is an example attribute */
        }
    }
}"""


USAGE = """package DummyUsageModel {
    private import DummyDefinitionModel::*;
    view def ViewUsage :> ViewDefinition {
        attribute :>> exampleAttribute = "Example Value";
    }
}"""


SUBSET_USAGE = """package DummySubsetModel {
    private import DummyDefinitionModel::*;
    part def Holder {
        attribute :> exampleAttribute = "Subset Value";
    }
}"""


def test_redefined_name_resolves_redefine():
    """``attribute :>> ea;`` → ``redefined_name == "ea"``."""
    model = loads(USAGE)
    view = model.get_child("DummyUsageModel.ViewUsage")
    attr = view.attributes[0]
    assert attr.redefined_name == "exampleAttribute"


def test_display_name_suppresses_uuid_for_redefined():
    """``display_name`` returns the user-visible name even when
    ``self.name`` is the UUID sentinel."""
    model = loads(USAGE)
    view = model.get_child("DummyUsageModel.ViewUsage")
    attr = view.attributes[0]
    # self.name stays the auto-generated UUID (backward-compatible)
    from sysmlpy.usage import _is_uuid
    assert _is_uuid(attr.name)
    # ...but display_name surfaces the redefined name:
    assert attr.display_name == "exampleAttribute"


def test_definition_attribute_name_unchanged():
    """For non-redeclared attributes, ``self.name`` already holds the
    identifier (from ``identification``); helpers must not regress."""
    model = loads(DEFINITION)
    view = model.get_child("DummyDefinitionModel.ViewDefinition")
    attr = view.attributes[0]
    assert attr.name == "exampleAttribute"
    assert attr.redefined_name == ""
    assert attr.display_name == "exampleAttribute"


def test_subset_chains_resolve_last_segment():
    """``attribute :> exampleAttribute;`` populates ``redefined_name``."""
    model = loads(SUBSET_USAGE)
    holder = model.get_child("DummySubsetModel.Holder")
    attr = holder.attributes[0]
    assert attr.redefined_name == "exampleAttribute"
    assert attr.display_name == "exampleAttribute"


def test_get_value_still_works_after_redefined_name():
    """The original report: ``get_value()`` already worked; confirm we
    didn't break it while adding the helpers."""
    model = loads(USAGE)
    view = model.get_child("DummyUsageModel.ViewUsage")
    attr = view.attributes[0]
    assert attr.get_value() == "Example Value"


def test_dump_still_emits_redefined_form():
    """Dump must continue to render ``attribute :>> exampleAttribute = ...;``
    regardless of how the helpers expose the name."""
    model = loads(USAGE)
    view = model.get_child("DummyUsageModel.ViewUsage")
    attr = view.attributes[0]
    assert "attribute :>> exampleAttribute=" in attr.dump()
    assert '"Example Value"' in attr.dump()

# References (v0.40.0+): ``ref attribute ::> X`` / ``ref attribute references X``
# is a type-only reference (no redefinition). The name surfaces via
# ``redefined_name`` because the grammar emits an ``OwnedReferenceSubsetting``
# with a ``referencedFeature`` QualifiedName — same shape as
# ``Redefinitions`` for name purposes.

REFERENCES_USAGE = """package P {
    ref attribute ::> MyType;
    ref attribute references OtherType;
}"""


def test_references_operator_resolves_via_redefined_name():
    model = loads(REFERENCES_USAGE)
    # ``ref attribute ::> X`` wraps the attribute in the ReferenceUsage;
    # use ``attributes`` (not ``find`` by name — ``name`` is a UUID sentinel
    # because no identification was given on the feature).
    def find_attrs(node):
        out = []
        if hasattr(node, 'attributes'):
            out.extend(node.attributes)
        for c in getattr(node, 'children', []):
            out.extend(find_attrs(c))
        return out
    attrs = find_attrs(model)
    names = sorted(a.redefined_name for a in attrs)
    assert names == ['MyType', 'OtherType']
    for a in attrs:
        assert a.display_name == a.redefined_name


def test_references_dump_emits_keyword():
    model = loads(REFERENCES_USAGE)
    dump = model.dump()
    assert '::> MyType' in dump
    # keyword form canonicalizes to the operator form
    assert '::> OtherType' in dump


# v0.41.0: full-specialization sweep across usage kinds — actions,
# requirements, constraints, calculations, use cases, interfaces now
# capture and render ``:>`` / ``:>>`` / ``::>`` at the API level.

def test_action_specializations_round_trip_api_level():
    """Action.dump() renders all four specialization kinds."""
    model = loads("""package P {
        action a1 :> BaseType;
        action a2 ::> RefType;
        action a3 :>> RedefType;
        action a4 : Real;
    }""")
    def find_actions(node):
        out = []
        if type(node).__name__ == 'Action':
            out.append(node)
        for c in getattr(node, 'children', []):
            out.extend(find_actions(c))
        return out
    dumps = {a.name: a.dump() for a in find_actions(model)}
    assert dumps['a1'] == 'action a1 :> BaseType;'
    assert dumps['a2'] == 'action a2 ::> RefType;'
    assert dumps['a3'] == 'action a3 :>> RedefType;'
    assert dumps['a4'] == 'action a4 : Real;'


def test_action_redefined_name_helper():
    """``redefined_name`` works on Action usages too."""
    model = loads("package P { action a :>> baseAction; }")
    def find_actions(node):
        out = []
        if type(node).__name__ == 'Action':
            out.append(node)
        for c in getattr(node, 'children', []):
            out.extend(find_actions(c))
        return out
    acts = find_actions(model)
    assert len(acts) == 1
    assert acts[0].redefined_name == 'baseAction'
