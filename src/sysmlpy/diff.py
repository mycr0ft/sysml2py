"""Semantic model diff for review workflows (Goal 8 + Goal 11 Batch 3).

Compares two loaded models element-by-element and reports what
changed, so review workflows (PR gates, design comparisons) can see
*semantic* changes rather than whitespace/formatting noise.

Element identity is ``(kind, qualified name)`` — ``Fleet::Vehicle``
as a ``PartDef`` is a different identity from a ``PartUsage`` with
the same name.  Every element carries a *signature* — the semantic
attributes the library tracks reliably:

- ``typing`` — the declared type name (``typed_by_name``, qualified)
- ``subject`` — requirement subjects (``(name, type)`` tuples)
- ``doc`` — documentation text (tree attribute; populated for
  requirement-style kinds)
- ``value`` — the default-value expression (``= 70``), from the
  element's dump text
- ``multiplicity`` — ``[2]``, ``[1..3] ordered nonunique`` etc.
- ``direction`` — ``in`` / ``out`` / ``inout`` feature direction
- ``abstract`` — ``abstract`` flag on definitions
- ``traces`` — requirement trace edges (``satisfy:x``, ``verify:y``)
  via :func:`sysmlpy.traceability.extract_traceability`

Value / multiplicity / direction / abstract are *heuristic* reads of
the element's canonical ``dump()`` text — the dump is the library's
own canonical serialization, so both sides of the diff extract the
same way.  The value regex does not span strings containing ``;``.
Documentation is *not* extracted from dumps — ``doc /* ... */``
members do not survive the grammar round-trip on usage/definition
kinds — so the ``doc`` field reflects the tree attribute (populated
for requirements).

Change kinds:

- ``added`` — element exists only in the new model
- ``removed`` — element exists only in the old model
- ``renamed`` — a removed/added pair matched by *rename detection*:
  same kind and same structural signature (everything except
  ``doc``, which often changes alongside a rename) with exactly one
  candidate.  Ambiguous matches (several candidates) stay
  removed + added.  ``old_name``/``old_qualified_name`` carry the
  previous identity; ``fields`` lists any signature drift.
- ``changed`` — same identity, different signature; ``fields`` lists
  the field-level old/new values

State machines: :func:`diff_state_machines` diffs two models' state
machines through the simulator's :class:`~sysmlpy.sim.MachineDescriptor`
— states, transitions (source/target/trigger/guard/effect/history)
and the initial state.

Excluded by design: ``Model`` objects carry a random UUID name per
parse, so they are never compared.

Usage::

    from sysmlpy.diff import diff_models, diff_files, diff_state_machines

    d = diff_models(old_model, new_model)
    print(d.as_text())
    d2 = diff_files("old.sysml", "new.sysml")
    md = diff_state_machines(old_model, new_model, focus="Cruise")

CLI: ``sysmlpy diff OLD NEW [--format text|markdown|json]
[--threshold 0.1]`` — with ``--threshold``, exit 1 only when the
change rate (changes / old elements) exceeds the gate.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

__all__ = [
    "FieldChange",
    "ElementChange",
    "ModelDiff",
    "diff_models",
    "diff_files",
    "diff_state_machines",
]


# ---------------------------------------------------------------------------
# data types
# ---------------------------------------------------------------------------


@dataclass
class FieldChange:
    """One changed field within an element."""

    field: str
    old: str | None
    new: str | None


@dataclass
class ElementChange:
    """One element-level semantic change."""

    change: str  # "added" | "removed" | "renamed" | "changed"
    kind: str  # e.g. "PartDef", "PartUsage", "Package", "Transition"
    name: str
    qualified_name: str
    fields: list = field(default_factory=list)  # list[FieldChange]
    #: previous name/qname — populated for ``renamed`` entries
    old_name: str | None = None
    old_qualified_name: str | None = None


@dataclass
class ModelDiff:
    """The semantic diff between two models."""

    changes: list = field(default_factory=list)  # list[ElementChange]
    #: number of comparable elements in the old/new models (for the
    #: ``--threshold`` change-rate gate)
    elements_old: int = 0
    elements_new: int = 0

    # ------------------------------------------------------------------
    # queries
    # ------------------------------------------------------------------

    @property
    def added(self) -> list:
        return [c for c in self.changes if c.change == "added"]

    @property
    def removed(self) -> list:
        return [c for c in self.changes if c.change == "removed"]

    @property
    def renamed(self) -> list:
        return [c for c in self.changes if c.change == "renamed"]

    @property
    def changed(self) -> list:
        return [c for c in self.changes if c.change == "changed"]

    def is_empty(self) -> bool:
        """True when the models are semantically identical."""
        return not self.changes

    @property
    def change_rate(self) -> float:
        """Fraction of the old model affected by this diff.

        ``changes / elements_old`` (0.0 when the old model is empty).
        Used by the ``--threshold`` CI gate.
        """
        if not self.elements_old:
            return 0.0 if not self.changes else 1.0
        return len(self.changes) / self.elements_old

    def summary(self) -> str:
        """One-line human summary, e.g. ``2 added, 1 removed, 3 changed``."""
        if self.is_empty():
            return "models are semantically identical"
        counts = [f"{len(self.added)} added",
                  f"{len(self.removed)} removed",
                  f"{len(self.renamed)} renamed",
                  f"{len(self.changed)} changed"]
        return ", ".join(counts)

    # ------------------------------------------------------------------
    # rendering
    # ------------------------------------------------------------------

    def as_text(self) -> str:
        """Plain-text rendering (monochrome — review-log friendly)."""
        if self.is_empty():
            return "models are semantically identical\n"
        marker = {"added": "+", "removed": "-", "renamed": ">",
                  "changed": "~"}
        out = [f"Model diff: {self.summary()}", ""]
        for c in self.changes:
            if c.change == "renamed":
                out.append(f"> {c.kind}  {c.old_qualified_name}"
                           f" -> {c.qualified_name}")
            else:
                out.append(f"{marker[c.change]} {c.kind}  "
                           f"{c.qualified_name}")
            for fc in c.fields:
                old_v = fc.old if fc.old is not None else "(none)"
                new_v = fc.new if fc.new is not None else "(none)"
                out.append(f"    {fc.field}: {old_v} -> {new_v}")
        return "\n".join(out) + "\n"

    def as_markdown(self) -> str:
        """Markdown rendering for review workflows (PR comments etc.)."""
        if self.is_empty():
            return "Models are semantically identical.\n"
        out = [f"## Model diff", "",
               f"**{self.summary()}**", ""]
        sections = [
            ("added", "### Added"),
            ("removed", "### Removed"),
            ("renamed", "### Renamed"),
            ("changed", "### Changed"),
        ]
        for kind, header in sections:
            items = [c for c in self.changes if c.change == kind]
            if not items:
                continue
            out.append(header)
            out.append("")
            for c in items:
                if kind == "renamed":
                    out.append(f"- `{c.old_qualified_name}` → "
                               f"`{c.qualified_name}` ({c.kind})")
                else:
                    out.append(f"- `{c.qualified_name}` ({c.kind})")
                for fc in c.fields:
                    old_v = fc.old if fc.old is not None else "—"
                    new_v = fc.new if fc.new is not None else "—"
                    out.append(
                        f"  - `{fc.field}`: `{old_v}` → `{new_v}`")
            out.append("")
        return "\n".join(out).rstrip() + "\n"


# ---------------------------------------------------------------------------
# signature extraction
# ---------------------------------------------------------------------------

_FIELDS = ("typing", "subject", "doc", "value", "multiplicity",
           "direction", "abstract", "traces")
#: fields used to match renames (``doc`` often changes with the name)
_STRUCTURAL = tuple(f for f in _FIELDS if f != "doc")

_DIR_RE = re.compile(r"^(?:in|out|inout)\b")
_MULT_RE = re.compile(r"\[([^\]]+)\]")
_VALUE_RE = re.compile(r"(?<![<>=!])=\s*([^;]+);\s*$")


def _kind(obj) -> str:
    """Element kind with a definition/usage suffix.

    ``PartDef`` / ``PartUsage`` — the same qualified name under both
    roles is a different identity, so e.g. turning ``part def X`` into
    an inline ``part x : X`` reports as removed + added, not changed.
    """
    base = type(obj).__name__
    return base + ("Def" if getattr(obj, "is_definition", False)
                   else "Usage")


def _dump_fields(obj) -> dict:
    """Heuristic signature fields read from the element's canonical dump.

    The dump is the library's own canonical serialization, so the same
    element dumps identically on both sides of a diff.  Only the first
    line is inspected for direction / multiplicity / value (usages are
    single-line); the first ``doc /* ... */`` comment anywhere is the
    element's own documentation in the common declaration order.
    """
    try:
        text = obj.dump()
    except Exception:
        return {}
    if not text or not text.strip():
        return {}
    first = text.strip().splitlines()[0].strip()
    out = {}


    m = _DIR_RE.match(first)
    out["direction"] = m.group(0) if m else None

    m = _MULT_RE.search(first)
    if m:
        flags = [f for f in ("ordered", "nonunique")
                 if re.search(rf"\b{f}\b", first)]
        out["multiplicity"] = f"[{m.group(1)}]" + (
            f" {' '.join(flags)}" if flags else "")
    else:
        out["multiplicity"] = None

    m = _VALUE_RE.search(first)
    out["value"] = m.group(1).strip() if m else None

    out["abstract"] = "abstract" if re.match(r"^abstract\b", first) else None

    return out


def _signature(obj, traces: dict | None = None) -> dict:
    """The comparable semantic attributes of a tree object."""
    sig = {}

    typing = getattr(obj, "typed_by_name", None)
    sig["typing"] = str(typing) if typing else None

    subject = getattr(obj, "subject", None)
    if subject:
        name, type_name = subject
        sig["subject"] = f"{name} : {type_name}" if type_name else str(name)
    else:
        sig["subject"] = None

    for f, v in _dump_fields(obj).items():
        sig[f] = v

    doc = getattr(obj, "doc", None)
    if doc:
        sig["doc"] = str(doc)

    sig["traces"] = None
    if traces:
        from sysmlpy.traceability import _qualified_name
        trace = traces.get(_qualified_name(obj))
        if trace is not None:
            edges = ([f"satisfy:{x}" for x in trace.satisfied_by] +
                     [f"verify:{x}" for x in trace.verified_by])
            if edges:
                sig["traces"] = ", ".join(sorted(edges))

    return sig


def _collect(model, traces: dict | None = None) -> dict:
    """Map ``(kind, qualified name)`` -> ``(name, signature)``."""
    from sysmlpy.traceability import _walk, _qualified_name

    out = {}
    for obj in _walk(model):
        if type(obj).__name__ == "Model":
            continue  # random UUID name — not comparable
        qname = _qualified_name(obj)
        if not qname:
            continue
        key = (_kind(obj), qname)
        out[key] = (getattr(obj, "name", ""), _signature(obj, traces))
    return out


# ---------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------


def diff_models(old_model: Any, new_model: Any) -> ModelDiff:
    """Diff two loaded models semantically.

    Parameters
    ----------
    old_model, new_model : Model
        Two models loaded via :func:`sysmlpy.loads` /
        :func:`sysmlpy.load_files` (or any Model tree).
    """
    from sysmlpy.traceability import extract_traceability

    old_traces = new_traces = None
    try:
        old_traces = {t.qualified_name: t
                      for t in extract_traceability(old_model).requirements}
        new_traces = {t.qualified_name: t
                      for t in extract_traceability(new_model).requirements}
    except Exception:
        old_traces = new_traces = None  # traces are best-effort

    old = _collect(old_model, old_traces)
    new = _collect(new_model, new_traces)

    # Rename detection: a removed element matches an added one when
    # kind AND structural signature are equal and the candidate is
    # unique — otherwise the pair stays removed + added.
    removed_keys = sorted(k for k in old if k not in new)
    added_keys = sorted(k for k in new if k not in old)
    matches: dict = {}
    used: set = set()
    for rk in removed_keys:
        sig_old = tuple(old[rk][1].get(f) for f in _STRUCTURAL)
        candidates = [
            ak for ak in added_keys
            if ak not in used and ak[0] == rk[0]
            and tuple(new[ak][1].get(f) for f in _STRUCTURAL) == sig_old
        ]
        if len(candidates) == 1:
            matches[rk] = candidates[0]
            used.add(candidates[0])

    matched_removed = set(matches)
    matched_added = set(matches.values())

    changes = []
    for key in sorted((set(old) | set(new))
                      - matched_removed - matched_added):
        in_old = key in old
        in_new = key in new
        kind, qname = key
        if in_old and not in_new:
            changes.append(ElementChange(
                change="removed", kind=kind,
                name=old[key][0], qualified_name=qname))
        elif in_new and not in_old:
            changes.append(ElementChange(
                change="added", kind=kind,
                name=new[key][0], qualified_name=qname))
        else:
            old_sig = old[key][1]
            new_sig = new[key][1]
            field_changes = [
                FieldChange(field=f, old=old_sig.get(f),
                            new=new_sig.get(f))
                for f in _FIELDS
                if old_sig.get(f) != new_sig.get(f)
            ]
            if field_changes:
                changes.append(ElementChange(
                    change="changed", kind=kind,
                    name=new[key][0], qualified_name=qname,
                    fields=field_changes))
    for rk in sorted(matched_removed):
        ak = matches[rk]
        kind = rk[0]
        old_sig = old[rk][1]
        new_sig = new[ak][1]
        field_changes = [
            FieldChange(field=f, old=old_sig.get(f), new=new_sig.get(f))
            for f in _FIELDS if old_sig.get(f) != new_sig.get(f)
        ]
        changes.append(ElementChange(
            change="renamed", kind=kind,
            name=new[ak][0], qualified_name=ak[1],
            old_name=old[rk][0], old_qualified_name=rk[1],
            fields=field_changes))

    return ModelDiff(changes=changes, elements_old=len(old),
                     elements_new=len(new))


def diff_files(old_path, new_path) -> ModelDiff:
    """Diff two SysML source files.

    Parameters
    ----------
    old_path, new_path : str | Path
        Paths to ``.sysml`` files.
    """
    import sysmlpy

    old_model = sysmlpy.loads(Path(old_path).read_text(encoding="utf-8"))
    new_model = sysmlpy.loads(Path(new_path).read_text(encoding="utf-8"))
    return diff_models(old_model, new_model)


# ---------------------------------------------------------------------------
# state-machine diff (Goal 11 Batch 3)
# ---------------------------------------------------------------------------

_TRANSITION_FIELDS = ("source", "target", "trigger", "guard", "effect",
                      "history_region")


def _transition_keys(descriptor) -> dict:
    """Identity for each transition (declaration order).

    Named transitions use their name; anonymous ones use
    ``transition@<source>-><target>``.  Duplicates get a ``#2``-style
    suffix so every identity is unique.
    """
    keys = {}
    seen: dict = {}
    for i, t in enumerate(descriptor.transitions):
        base = t.name or f"transition@{t.source}->{t.target}"
        n = seen.get(base, 0)
        seen[base] = n + 1
        keys[i] = base if n == 0 else f"{base}#{n + 1}"
    return keys


def diff_state_machines(old_model: Any, new_model: Any,
                        focus: str | None = None) -> ModelDiff:
    """Diff the state machines of two models.

    Compares the machines through the simulator's extraction
    (:func:`sysmlpy.sim.build_state_machine`): states, transitions
    (source/target/trigger/guard/effect/history) and the initial
    state.  Transitions are identified by declaration name (anonymous
    ones by their endpoints).

    Raises :class:`sysmlpy.sim.SimulationError` when either model has
    no (matching) state machine or declares parallel regions.
    """
    from sysmlpy.sim import build_state_machine

    old_md = build_state_machine(old_model, focus=focus)
    new_md = build_state_machine(new_model, focus=focus)

    changes = []
    machine_name = new_md.name or old_md.name or ""
    if old_md.initial != new_md.initial:
        changes.append(ElementChange(
            change="changed", kind="StateMachine", name=machine_name,
            qualified_name=machine_name,
            fields=[FieldChange(field="initial", old=old_md.initial,
                                new=new_md.initial)]))

    old_states = set(old_md.states)
    new_states = set(new_md.states)
    for s in sorted(old_states - new_states):
        changes.append(ElementChange(change="removed", kind="State",
                                     name=s, qualified_name=s))
    for s in sorted(new_states - old_states):
        changes.append(ElementChange(change="added", kind="State",
                                     name=s, qualified_name=s))

    old_keys = _transition_keys(old_md)
    new_keys = _transition_keys(new_md)
    old_t = {old_keys[i]: t for i, t in enumerate(old_md.transitions)}
    new_t = {new_keys[i]: t for i, t in enumerate(new_md.transitions)}

    for key in sorted(set(old_t) | set(new_t)):
        in_old, in_new = key in old_t, key in new_t
        if in_old and not in_new:
            changes.append(ElementChange(
                change="removed", kind="Transition", name=key,
                qualified_name=key))
        elif in_new and not in_old:
            changes.append(ElementChange(
                change="added", kind="Transition", name=key,
                qualified_name=key))
        else:
            o, n = old_t[key], new_t[key]
            field_changes = [
                FieldChange(field=f, old=getattr(o, f),
                            new=getattr(n, f))
                for f in _TRANSITION_FIELDS
                if getattr(o, f) != getattr(n, f)
            ]
            if field_changes:
                changes.append(ElementChange(
                    change="changed", kind="Transition", name=key,
                    qualified_name=key, fields=field_changes))

    return ModelDiff(changes=changes, elements_old=len(old_md.states),
                     elements_new=len(new_md.states))