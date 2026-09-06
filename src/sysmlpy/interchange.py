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

The ``@vocab`` IRI space is sysmlpy-owned.  No OMG-published JSON-LD
context file exists to bundle (checked against the SysML v2 pilot
implementation, which carries none), so v0.85.0 makes the vocabulary
configurable and adds an explicit per-property term-definition builder
(:func:`build_jsonld_context`): documents can carry full
``<vocabulary>#<property>`` IRIs for every property and metaclass, in
the OMG JSON-LD vocabulary style, and import side normalizes IRI-keyed
properties back to local names.

Public surface:

- :func:`to_interchange` — ``Model`` or SysML text → interchange dict
- :func:`from_interchange` — interchange dict / JSON text → ``Model``
- :func:`interchange_to_json_text` / convenience formatting helpers
- :func:`build_jsonld_context` — explicit property/metaclass IRI map
- :func:`INTERCHANGE_VOCABULARY` — default vocabulary IRI (constant)
"""

from __future__ import annotations

import json as _json
import uuid as _uuid

__all__ = [
    "INTERCHANGE_CONTEXT",
    "INTERCHANGE_VOCABULARY",
    "INTERCHANGE_NAMESPACE",
    "to_interchange",
    "from_interchange",
    "interchange_to_json_text",
    "build_jsonld_context",
]

#: JSON-LD context emitted with every document.  Property names are the
#: SysML v2 abstract-syntax property names used by the parser; the
#: vocabulary IRI is sysmlpy-owned.  Pass ``vocabulary=...`` to
#: :func:`to_interchange` / :func:`build_jsonld_context` to emit IRIs
#: under a different (e.g. OMG-published) vocabulary instead.
INTERCHANGE_CONTEXT = {
    "@version": 1.1,
    "@vocab": "https://github.com/mycr0ft/sysmlpy/interchange#",
}

#: Default vocabulary IRI every property/metaclass term resolves
#: against (same space as :data:`INTERCHANGE_CONTEXT` ``@vocab``).
INTERCHANGE_VOCABULARY = INTERCHANGE_CONTEXT["@vocab"]

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


def build_jsonld_context(document=None, *, vocabulary=None,
                         properties=None, types=None):
    """Build an explicit JSON-LD context mapping names to IRIs.

    Every SysML v2 property name and metaclass ``@type`` value maps to
    ``<vocabulary>#<name>`` — the OMG JSON-LD vocabulary convention —
    so the document is self-describing for RDF / JSON-LD tooling
    without relying on ``@vocab`` alone.

    Parameters
    ----------
    document : dict, optional
        Derive the property and type name lists from an interchange
        document (its ``@graph`` is scanned).
    vocabulary : str, optional
        Vocabulary IRI base (default :data:`INTERCHANGE_VOCABULARY`).
        Point this at an OMG-published SysML vocabulary IRI when one
        is available; no normative OMG context file currently exists
        to bundle, so the mapping stays configurable by design.
    properties, types : iterable of str, optional
        Explicit name lists (override ``document`` derivation).

    Returns
    -------
    dict
        ``{"@version": 1.1, "@vocab": ..., "prop": {"@id": ...}, ...}``
    """
    vocab = (vocabulary or INTERCHANGE_VOCABULARY).rstrip("/#")
    if properties is None or types is None:
        doc_props, doc_types = _document_terms(document)
        if properties is None:
            properties = sorted(doc_props)
        if types is None:
            types = sorted(doc_types)
    context = {
        "@version": 1.1,
        "@vocab": vocab + "#",
    }
    for prop in properties:
        if not str(prop).startswith("@"):
            context[str(prop)] = {"@id": f"{vocab}#{prop}"}
    for type_name in types:
        context[str(type_name)] = {"@id": f"{vocab}#{type_name}"}
    return context


def _document_terms(document):
    """Property names and ``@type`` values used inside a document."""
    props = set()
    types = set()
    if not isinstance(document, dict):
        return props, types
    for elem in document.get("@graph", []) or []:
        if not isinstance(elem, dict):
            continue
        type_name = elem.get("@type")
        if isinstance(type_name, str):
            types.add(type_name)
        for key, value in elem.items():
            if key.startswith("@"):
                continue
            props.add(key)
            # nested structures may carry further property names
            _collect_terms(value, props)
    return props, types


def _collect_terms(value, props):
    if isinstance(value, dict):
        for k, v in value.items():
            if not str(k).startswith("@"):
                props.add(k)
            _collect_terms(v, props)
    elif isinstance(value, list):
        for item in value:
            _collect_terms(item, props)


def _extract_properties(source):
    """Derive property/type names for term generation from a source."""
    try:
        document = to_interchange(source)
    except Exception:
        return None, None
    props, types = _document_terms(document)
    return props, types


def to_interchange(source, *, vocabulary=None, explicit_terms=False):
    """Export a model to the SysML v2 JSON interchange representation.

    Parameters
    ----------
    source : Model or str
        Either a loaded model (``sysmlpy.loads(...)`` / ``load_files(...)``
        / programmatically built) or SysML v2 source text (parsed fresh).
    vocabulary : str, optional
        Vocabulary IRI for the ``@vocab`` mapping (default
        :data:`INTERCHANGE_VOCABULARY`).
    explicit_terms : bool
        When true, the ``@context`` additionally carries explicit
        ``property → <vocabulary>#property`` term definitions for
        every property and metaclass in the document (see
        :func:`build_jsonld_context`).

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
    context = dict(INTERCHANGE_CONTEXT)
    if vocabulary:
        context["@vocab"] = vocabulary.rstrip("/#") + "#"
    if explicit_terms:
        context = build_jsonld_context(
            {"@graph": graph}, vocabulary=vocabulary
        )
    return {
        "@context": context,
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


def from_interchange(data, *, vocabulary=None) -> "Model":
    """Import a SysML v2 JSON interchange document into a live Model.

    Parameters
    ----------
    data : dict or str
        The interchange document (as produced by :func:`to_interchange`),
        either as a dict or as a JSON string.  Documents whose property
        keys are written as full IRIs (``<vocab>#<property>`` — see
        :func:`build_jsonld_context`) are normalized automatically when
        the IRI prefix matches the document's ``@vocab`` or the
        ``vocabulary`` argument.
    vocabulary : str, optional
        Vocabulary IRI to recognize when normalizing IRI-keyed
        properties (in addition to the document's own ``@vocab``).

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

    # Normalize IRI-keyed property names (external JSON-LD documents
    # write <vocab>#<prop>; the internal dict uses bare names).
    vocabs = _context_vocabularies(data, vocabulary)
    if vocabs:
        graph = [_normalize_keys(elem, vocabs) for elem in graph]
        data = {**data, "@graph": graph}

    root_ref = data.get("@id")
    if root_ref is None:
        # Fall back to the first element that is not referenced by others.
        referenced = {
            v["@id"]
            for elem in graph
            for v in _walk_refs(elem)
            if isinstance(v, dict) and "@id" in v
        }
        roots = [e["@id"] for e in graph if isinstance(e, dict) and "@id" in e and e["@id"] not in referenced]
        if not roots:
            raise ValueError("Cannot determine root element of document")
        root_ref = roots[0]
    # @id values themselves can be IRI-keyed in external documents
    root_ref = _strip_vocabulary(root_ref, vocabs)

    by_id = {}
    for elem in graph:
        if not isinstance(elem, dict) or "@id" not in elem:
            raise ValueError("Every @graph element needs an @id")
        by_id[elem["@id"]] = elem

    root = _rebuild({"@id": root_ref}, by_id)
    relationships = root.get("ownedRelationship")
    if relationships is None:
        raise ValueError(
            "Root element carries no ownedRelationship — not a model document"
        )

    model = Model()
    return model._load_definition(relationships)


def _context_vocabularies(data, extra=None):
    """Vocabulary IRIs to normalize against (document @vocab + extras)."""
    vocabs = set()
    context = data.get("@context")
    if isinstance(context, dict):
        vocab = context.get("@vocab")
        if isinstance(vocab, str) and "#" in vocab:
            vocabs.add(vocab)
    if isinstance(extra, str):
        vocabs.add(extra.rstrip("/#") + "#")
    return vocabs


def _normalize_keys(elem, vocabs):
    """Strip known vocabulary prefixes from property/type keys."""
    if isinstance(elem, dict):
        out = {}
        for key, value in elem.items():
            if key == "@type" and isinstance(value, str):
                out[key] = _strip_vocabulary(value, vocabs)
            else:
                out[_strip_vocabulary(key, vocabs)] = \
                    _normalize_keys(value, vocabs)
        return out
    if isinstance(elem, list):
        return [_normalize_keys(item, vocabs) for item in elem]
    return elem


def _strip_vocabulary(key, vocabs):
    if isinstance(key, str) and "#" in key:
        for vocab in vocabs:
            if key.startswith(vocab):
                return key[len(vocab):]
    return key


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