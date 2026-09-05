"""Semantic model diff for review workflows (Goal 8).

Compares two loaded models element-by-element and reports what
changed, so review workflows (PR gates, design comparisons) can see
*semantic* changes rather than whitespace/formatting noise.

Element identity is ``(kind, qualified name)`` — ``Fleet::Vehicle``
as a ``PartDef`` is a different identity from a ``PartUsage`` with
the same name.  Every element carries a *signature* — the semantic
attributes the library tracks reliably on tree objects:

- ``typing`` — the declared type name (``typed_by_name``, qualified)
- ``subject`` — requirement subjects (``(name, type)`` tuples)
- ``doc`` — documentation text when present

Change kinds:

- ``added`` — element exists only in the new model
- ``removed`` — element exists only in the old model
- ``changed`` — same identity, different signature; ``fields`` lists
  the field-level old/new values

Renames surface as a removed/added pair (rename detection needs
heuristic matching — a tracked follow-up, not MVP).

Excluded by design:

- ``Model`` objects carry a random UUID name per parse, so they are
  never compared.
- Transitions are not tree objects (like verify members, they ride
  the grammar dicts); state-machine diffs need the simulator's
  machine descriptors — a tracked follow-up.
- Values, multiplicities and directions live in grammar dicts, not
  on tree objects — grammar-level diffs are a follow-up batch.

Usage::

    from sysmlpy.diff import diff_models, diff_files

    d = diff_models(old_model, new_model)
    print(d.as_text())
    d2 = diff_files("old.sysml", "new.sysml")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

__all__ = [
    "FieldChange",
    "ElementChange",
    "ModelDiff",
    "diff_models",
    "diff_files",
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

    change: str  # "added" | "removed" | "changed"
    kind: str  # e.g. "PartDef", "PartUsage", "Package"
    name: str
    qualified_name: str
    fields: list = field(default_factory=list)  # list[FieldChange]


@dataclass
class ModelDiff:
    """The semantic diff between two models."""

    changes: list = field(default_factory=list)  # list[ElementChange]

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
    def changed(self) -> list:
        return [c for c in self.changes if c.change == "changed"]

    def is_empty(self) -> bool:
        """True when the models are semantically identical."""
        return not self.changes

    def summary(self) -> str:
        """One-line human summary, e.g. ``2 added, 1 removed, 3 changed``."""
        counts = [f"{len(self.added)} added",
                  f"{len(self.removed)} removed",
                  f"{len(self.changed)} changed"]
        if self.is_empty():
            return "models are semantically identical"
        return ", ".join(counts)

    # ------------------------------------------------------------------
    # rendering
    # ------------------------------------------------------------------

    def as_text(self) -> str:
        """Plain-text rendering (monochrome — review-log friendly)."""
        if self.is_empty():
            return "models are semantically identical\n"
        marker = {"added": "+", "removed": "-", "changed": "~"}
        out = [f"Model diff: {self.summary()}", ""]
        for c in self.changes:
            out.append(f"{marker[c.change]} {c.kind}  {c.qualified_name}")
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
            ("changed", "### Changed"),
        ]
        for kind, header in sections:
            items = [c for c in self.changes if c.change == kind]
            if not items:
                continue
            out.append(header)
            out.append("")
            for c in items:
                out.append(f"- `{c.qualified_name}` ({c.kind})")
                for fc in c.fields:
                    old_v = fc.old if fc.old is not None else "—"
                    new_v = fc.new if fc.new is not None else "—"
                    out.append(
                        f"  - `{fc.field}`: `{old_v}` → `{new_v}`")
            out.append("")
        return "\n".join(out).rstrip() + "\n"


# ---------------------------------------------------------------------------
# collection
# ---------------------------------------------------------------------------

_FIELDS = ("typing", "subject", "doc")


def _kind(obj) -> str:
    """Element kind with a definition/usage suffix.

    ``PartDef`` / ``PartUsage`` — the same qualified name under both
    roles is a different identity, so e.g. turning ``part def X`` into
    an inline ``part x : X`` reports as removed + added, not changed.
    """
    base = type(obj).__name__
    return base + ("Def" if getattr(obj, "is_definition", False)
                   else "Usage")


def _signature(obj) -> dict:
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

    doc = getattr(obj, "doc", None)
    sig["doc"] = str(doc) if doc else None

    return sig


def _collect(model) -> dict:
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
        out[key] = (getattr(obj, "name", ""), _signature(obj))
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
    old = _collect(old_model)
    new = _collect(new_model)

    changes = []
    for key in sorted(set(old) | set(new)):
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
    return ModelDiff(changes=changes)


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