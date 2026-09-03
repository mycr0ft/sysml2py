#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SysML v2 JSON interchange for sysmlpy (v0.63.0 — Adoption Roadmap Goal 3).

Exports a loaded model to a JSON-LD-style *partition interchange*
document in the style of the SysML v2 spec's JSON exchange format, and
imports such a document back into a live :class:`~sysmlpy.definition.Model`
— losslessly, with deterministic element identifiers.

Document shape::

    {
      "@context": {"@version": 1.1, "@vocab": "..."},
      "@id": "id:root",
      "@graph": [
        {"@id": "id:pkg-1", "@type": "Package", "declaredName": "P",
         "ownedRelationship": [{"@id": "id:rel-1"}]},
        {"@id": "id:rel-1", "@type": "OwningMembership",
         "ownedRelatedElement": {"@id": "id:part-1"}},
        {"@id": "id:part-1", "@type": "PartDefinition", ...},
        ...
      ]
    }

Design notes:

- **Flat graph.** Every element (packages, relationships, declarations,
  bodies, ...) appears exactly once in ``@graph``; structural properties
  reference other elements by ``{"@id": ...}``.  Scalars (``declaredName``,
  ``declaredShortName``, keywords, ...) are kept inline.  ``null`` values
  are preserved so the export/rebuild is shape-exact.
- **``@type``** is the SysML v2 abstract-syntax metaclass name, exactly
  as the parser's internal dictionary uses it (``Package``,
  ``OwningMembership``, ``PartDefinition``, ...).
- **Deterministic ``@id``s.**  Element identifiers are ``uuid5`` derived
  from the element's position in the model tree, so exporting the same
  model twice yields byte-identical JSON (diff-friendly, ties into
  semantic model diff — roadmap Goal 8).
- **Round-trip.**  ``from_interchange(to_interchange(model))`` rebuilds
  the internal dictionary shape-exactly and constructs a live ``Model``
  through the same grammar-class path as a fresh parse
  (``Model._load_definition``).

The ``@vocab`` IRI space is sysmlpy-owned; mapping every property to the
normative OMG JSON-LD context is tracked as follow-up work.

Public surface:

- :func:`to_interchange` — ``Model`` or SysML text → interchange dict
- :func:`from_interchange` — interchange dict / JSON text → ``Model``
- :func:`interchange_to_json_text` / convenience formatting helpers
"""

from __future__ import annotations

import json as _json
import uuid as _uuid

__all__ = [
    "INTERCHANGE_CONTEXT",
    "INTERCHANGE_NAMESPACE",
    "to_interchange",
    "from_interchange",
    "interchange_to_json_text",
]

#: JSON-LD context emitted with every document.  Property names are the
#: SysML v2 abstract-syntax property names used by the parser; the
#: vocabulary IRI is sysmlpy-owned (normative OMG context mapping is
#: tracked as follow-up work).
INTERCHANGE_CONTEXT = {
    "@version": 1.1,
    "@vocab": "https://github.com/mycr0ft/sysmlpy/interchange#",
}

#: UUID namespace for deterministic element identifiers.
INTERCHANGE_NAMESPACE = _uuid.uuid5(
    _uuid.NAMESPACE_URL, "https://github.com/mycr0ft/sysmlpy/interchange"
)

_REF_KEYS = ("@id", "@type")


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------


def _child_id(parent_id: str, key: str, index: int) -> str:
    """Deterministic identifier for the child at ``parent.key[index]``."""
    return "sysml:" + str(
        _uuid.uuid5(INTERCHANGE_NAMESPACE, f"{parent_id}|{key}|{index}")
    )


def _flatten(node: dict, parent_id: str, key: str, index: int,
             graph: list) -> str:
    """Recursively flatten a visitor-dict node into the graph.

    Returns the ``@id`` assigned to this node.
    """
    elem_id = _child_id(parent_id, key, index)
    elem = {"@id": elem_id, "@type": node.get("name")}
    for k, v in node.items():
        if k == "name":
            continue  # captured as @type
        elem[k] = _flatten_value(v, elem_id, k, graph)
    graph.append(elem)
    return elem_id


def _flatten_value(v, elem_id: str, key: str, graph: list):
    """Flatten one property value: dicts become @id refs, scalars inline."""
    if v is None or isinstance(v, (str, int, float, bool)):
        return v
    if isinstance(v, dict):
        return {"@id": _flatten(v, elem_id, key, 0, graph)}
    if isinstance(v, list):
        out = []
        for i, item in enumerate(v):
            if isinstance(item, dict):
                out.append({"@id": _flatten(item, elem_id, key, i, graph)})
            else:
                out.append(item)
        return out
    # Unknown value type — keep it inline (best effort).
    return v


def to_interchange(source) -> dict:
    """Export a model to the SysML v2 JSON interchange representation.

    Parameters
    ----------
    source : Model or str
        Either a loaded model (``sysmlpy.loads(...)`` / ``load_files(...)``
        / programmatically built) or SysML v2 source text (parsed fresh).

    Returns
    -------
    dict
        JSON-LD-style document: ``@context``, root ``@id`` and a flat
        ``@graph`` of elements.
    """
    from sysmlpy.definition import Model

    if isinstance(source, Model):
        # Export from the *raw parser dict*, not the grammar classes'
        # ``get_definition()`` output: the class serialization normalizes
        # the tree (adds ``ownedRelationship`` keys, unwraps
        # ``OccurrenceUsageElement``), which changes how classes
        # re-dispatch on import (e.g. satisfy wrappers were lost).
        # ``dump()`` is the canonical serialization — re-parsing it gives
        # the same dictionary shape a fresh parse produces.
        try:
            text = source.dump()
        except ValueError:
            text = ""  # empty model (dump raises "no elements to output")
        if not text.strip():
            root_dict = {
                "name": "PackageBodyElement",
                "ownedRelationship": [],
            }
        else:
            from sysmlpy import load_grammar
            root_dict = load_grammar(text)
    elif isinstance(source, str):
        from sysmlpy import load_grammar
        root_dict = load_grammar(source)
    else:
        raise TypeError(
            "to_interchange expects a Model or SysML text, "
            f"not {source.__class__.__name__}"
        )

    graph: list = []
    root_id = _flatten(root_dict, "root", "ownedRelationship", 0, graph)
    return {
        "@context": dict(INTERCHANGE_CONTEXT),
        "@id": root_id,
        "@graph": graph,
    }


def interchange_to_json_text(document: dict, *, indent: int = 2) -> str:
    """Serialize an interchange document to a JSON string."""
    return _json.dumps(document, indent=indent)


# ---------------------------------------------------------------------------
# import
# ---------------------------------------------------------------------------


def _is_ref(v) -> bool:
    return isinstance(v, dict) and set(v.keys()) == {"@id"}


def _rebuild(ref: dict, by_id: dict, stack: tuple = ()) -> dict:
    """Rebuild the internal-dict node referenced by ``ref``."""
    elem_id = ref["@id"]
    if elem_id in stack:
        raise ValueError(f"Cyclic element reference detected: {elem_id}")
    elem = by_id.get(elem_id)
    if elem is None:
        raise ValueError(f"Interchange document references unknown @id: {elem_id}")
    node = {"name": elem.get("@type")}
    for k, v in elem.items():
        if k in _REF_KEYS:
            continue
        node[k] = _rebuild_value(v, by_id, stack + (elem_id,))
    return node


def _rebuild_value(v, by_id: dict, stack: tuple):
    if _is_ref(v):
        return _rebuild(v, by_id, stack)
    if isinstance(v, list):
        return [
            _rebuild(i, by_id, stack) if _is_ref(i) else i for i in v
        ]
    return v


def from_interchange(data) -> "Model":
    """Import a SysML v2 JSON interchange document into a live Model.

    Parameters
    ----------
    data : dict or str
        The interchange document (as produced by :func:`to_interchange`),
        either as a dict or as a JSON string.

    Returns
    -------
    Model
    """
    from sysmlpy.definition import Model

    if isinstance(data, str):
        data = _json.loads(data)
    if not isinstance(data, dict):
        raise ValueError(
            "Interchange document must be a dict or JSON string, "
            f"got {type(data).__name__}"
        )
    graph = data.get("@graph")
    if not isinstance(graph, list):
        raise ValueError("Interchange document has no @graph array")
    by_id = {}
    for elem in graph:
        if not isinstance(elem, dict) or "@id" not in elem:
            raise ValueError("Every @graph element needs an @id")
        by_id[elem["@id"]] = elem

    root_ref = data.get("@id")
    if root_ref is None:
        # Fall back to the first element that is not referenced by others.
        referenced = {
            v["@id"]
            for elem in graph
            for v in _walk_refs(elem)
        }
        roots = [e["@id"] for e in graph if e["@id"] not in referenced]
        if not roots:
            raise ValueError("Cannot determine root element of document")
        root_ref = roots[0]

    root = _rebuild({"@id": root_ref}, by_id)
    relationships = root.get("ownedRelationship")
    if relationships is None:
        raise ValueError(
            "Root element carries no ownedRelationship — not a model document"
        )

    model = Model()
    return model._load_definition(relationships)


def _walk_refs(elem: dict):
    """Yield every ``{"@id": ...}`` ref reachable from *elem*'s properties."""
    for v in elem.values():
        yield from _walk_refs_value(v)


def _walk_refs_value(v):
    if _is_ref(v):
        yield v
    elif isinstance(v, list):
        for item in v:
            yield from _walk_refs_value(item)
    elif isinstance(v, dict):
        for item in v.values():
            yield from _walk_refs_value(item)