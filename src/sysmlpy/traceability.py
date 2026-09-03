#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Requirement traceability and verification coverage for sysmlpy.

Implements Adoption Roadmap Goal 2 (v0.62.0): traverse the satisfy and
verify relationships in a loaded model and produce coverage reports and
traceability matrices.

The public surface:

- :func:`extract_traceability` — build a :class:`TraceabilityReport` from
  a loaded model (the result of ``loads()`` / ``load_files()``).
- :class:`TraceabilityReport` — per-requirement traces plus coverage
  queries (``uncovered()``, ``unsatisfied()``, ``unverified()``,
  ``coverage()``) and output helpers (``to_markdown()``, ``to_json()``).
- :func:`as_traceability_matrix_view` — a requirements × coverage matrix
  in PlantUML, Markdown or HTML.

Exit-code semantics for CI use are provided by the ``sysmlpy trace``
CLI command (see ``sysmlpy.__main__``).
"""

from __future__ import annotations

import json as _json
from dataclasses import dataclass, field

__all__ = [
    "RequirementTrace",
    "TraceabilityReport",
    "extract_traceability",
    "as_traceability_matrix_view",
]


@dataclass
class RequirementTrace:
    """Traceability record for a single requirement.

    Attributes
    ----------
    name : str
        Declared requirement name (may be a generated UUID sentinel for
        anonymous requirements).
    qualified_name : str
        ``Package::...::name`` path of the requirement.
    text : str or None
        Requirement documentation (``doc /* ... */``) text, if any.
    subject : tuple or None
        ``(name, type)`` of the requirement's subject member, if declared.
    satisfied_by : list of str
        Names of the subjects (parts/usages) with ``satisfy <this> by ...``
        relationships.
    verified_by : list of str
        Names referenced by ``verify ...`` members inside the requirement.
    is_definition : bool
        True when the requirement is a ``requirement def``.
    """

    name: str
    qualified_name: str = ""
    text: str = None
    subject: tuple = None
    satisfied_by: list = field(default_factory=list)
    verified_by: list = field(default_factory=list)
    is_definition: bool = False

    @property
    def status(self) -> str:
        """Coverage status: covered / partial / uncovered.

        - **covered** — satisfied *and* verified
        - **partial** — satisfied or verified, but not both
        - **uncovered** — neither
        """
        sat = bool(self.satisfied_by)
        ver = bool(self.verified_by)
        if sat and ver:
            return "covered"
        if sat or ver:
            return "partial"
        return "uncovered"


@dataclass
class TraceabilityReport:
    """Requirement traceability report for a whole model."""

    requirements: list = field(default_factory=list)

    # ------------------------------------------------------------------
    # queries
    # ------------------------------------------------------------------

    def by_name(self, name: str):
        """Return the trace for *name*, or None."""
        for trace in self.requirements:
            if trace.name == name:
                return trace
        return None

    def coverage(self) -> dict:
        """Coverage summary counts.

        Returns a dict with ``total``, ``covered``, ``partial``,
        ``uncovered`` and ``coverage_ratio`` (0.0–1.0, covered/total).
        """
        total = len(self.requirements)
        counts = {"covered": 0, "partial": 0, "uncovered": 0}
        for trace in self.requirements:
            counts[trace.status] += 1
        return {
            "total": total,
            **counts,
            "coverage_ratio": (counts["covered"] / total) if total else 0.0,
        }

    def uncovered(self) -> list:
        """Requirements with no satisfy *and* no verify relationships."""
        return [t for t in self.requirements if t.status == "uncovered"]

    def unsatisfied(self) -> list:
        """Requirements not satisfied by any subject."""
        return [t for t in self.requirements if not t.satisfied_by]

    def unverified(self) -> list:
        """Requirements not verified by any verification case."""
        return [t for t in self.requirements if not t.verified_by]

    # ------------------------------------------------------------------
    # output
    # ------------------------------------------------------------------

    def to_json(self) -> dict:
        """Machine-readable report (for ``sysmlpy trace --format json``)."""
        return {
            "summary": self.coverage(),
            "requirements": [
                {
                    "name": t.name,
                    "qualified_name": t.qualified_name,
                    "text": t.text,
                    "subject": list(t.subject) if t.subject else None,
                    "satisfied_by": list(t.satisfied_by),
                    "verified_by": list(t.verified_by),
                    "status": t.status,
                    "is_definition": t.is_definition,
                }
                for t in self.requirements
            ],
        }

    def to_markdown(self) -> str:
        """Requirements × coverage table (GitHub-flavored Markdown)."""
        lines = [
            "| Requirement | Status | Satisfied by | Verified by | Subject |",
            "|-------------|--------|--------------|-------------|---------|",
        ]
        for t in self.requirements:
            sat = ", ".join(t.satisfied_by) if t.satisfied_by else "—"
            ver = ", ".join(t.verified_by) if t.verified_by else "—"
            subj = t.subject[0] if t.subject else "—"
            name = t.qualified_name or t.name
            lines.append(
                f"| {name} | {t.status} | {sat} | {ver} | {subj} |"
            )
        cov = self.coverage()
        lines.append("")
        lines.append(
            f"**Coverage:** {cov['covered']}/{cov['total']} covered, "
            f"{cov['partial']} partial, {cov['uncovered']} uncovered "
            f"({cov['coverage_ratio']:.0%})"
        )
        return "\n".join(lines)

    def to_text(self) -> str:
        """Plain-text report (default ``sysmlpy trace`` output)."""
        lines = []
        cov = self.coverage()
        lines.append(
            f"Requirement traceability: {cov['total']} requirements, "
            f"{cov['covered']} covered, {cov['partial']} partial, "
            f"{cov['uncovered']} uncovered"
        )
        if not self.requirements:
            lines.append("  (no requirements found)")
        for t in self.requirements:
            lines.append(f"- {t.qualified_name or t.name} [{t.status}]")
            if t.text:
                text = t.text if len(t.text) <= 72 else t.text[:69] + "..."
                lines.append(f"    text: {text}")
            if t.subject:
                name, typed = t.subject
                shown = f"{name}" + (f" : {typed}" if typed and typed != name else "")
                lines.append(f"    subject: {shown}")
            lines.append(
                f"    satisfied by: "
                f"{', '.join(t.satisfied_by) if t.satisfied_by else '(none)'}"
            )
            lines.append(
                f"    verified by: "
                f"{', '.join(t.verified_by) if t.verified_by else '(none)'}"
            )
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# extraction
# ---------------------------------------------------------------------------


def _qualified_name(obj) -> str:
    """Build ``Package::...::name`` from the object's parent chain."""
    segments = []
    node = obj
    while node is not None:
        name = getattr(node, "name", None)
        cls = node.__class__.__name__
        if cls == "Model":
            break
        if name:
            segments.append(name)
        node = getattr(node, "parent", None)
    return "::".join(reversed(segments))


def _last_segment(ref: str) -> str:
    """Last segment of a dotted/qualified reference (``Pkg::r1`` → ``r1``)."""
    for sep in ("::", "."):
        if sep in ref:
            ref = ref.rsplit(sep, 1)[-1]
    return ref


def _walk(obj):
    """Yield every object in the model tree (depth-first)."""
    yield obj
    for child in getattr(obj, "children", None) or []:
        yield from _walk(child)


def _extract_satisfy_edges(obj, traces_by_name, report_reqs):
    """Attach satisfy edges (grammar SatisfyRequirementUsage) to traces."""
    grammar = getattr(obj, "grammar", None)
    if grammar is None or grammar.__class__.__name__ != "SatisfyRequirementUsage":
        return
    ors = getattr(grammar, "ors", None)
    ssm = getattr(grammar, "ssm", None)
    req_ref = ors.dump().strip().rstrip(";").strip() if ors is not None else None
    subject = ssm.dump().strip().rstrip(";").strip() if ssm is not None else None
    if not req_ref:
        return
    target_name = _last_segment(req_ref)
    trace = traces_by_name.get(target_name)
    if trace is None:
        # The requirement lives outside this model (or is forward-declared);
        # still record the edge so the report is complete.
        trace = traces_by_name.get(req_ref)
    if trace is None:
        trace = RequirementTrace(name=target_name, qualified_name=req_ref)
        traces_by_name[target_name] = trace
        report_reqs.append(trace)
    if subject and subject not in trace.satisfied_by:
        trace.satisfied_by.append(subject)


def extract_traceability(model) -> TraceabilityReport:
    """Build a :class:`TraceabilityReport` from a loaded model.

    Parameters
    ----------
    model : Model
        A loaded model (``sysmlpy.loads(...)`` / ``load_files(...)``).

    Returns
    -------
    TraceabilityReport
    """
    traces = []
    traces_by_name = {}

    # Pass 1: collect requirements (Requirement objects whose grammar is a
    # RequirementDefinition / RequirementUsage — satisfy/verify wrappers are
    # also Requirement-typed but carry different grammar classes).
    for obj in _walk(model):
        if obj.__class__.__name__ != "Requirement":
            continue
        grammar = getattr(obj, "grammar", None)
        gclass = grammar.__class__.__name__ if grammar is not None else ""
        if gclass not in ("RequirementDefinition", "RequirementUsage"):
            continue
        qualified = _qualified_name(obj)
        name = obj.name
        trace = RequirementTrace(
            name=name,
            qualified_name=qualified,
            text=getattr(obj, "doc", None),
            subject=getattr(obj, "subject", None),
            verified_by=list(getattr(obj, "verified_by", None) or []),
            is_definition=(gclass == "RequirementDefinition"),
        )
        traces.append(trace)
        # Index by both the bare name and every suffix of the qualified
        # name so `Pkg::req` / `req` / `Sub::req` references all resolve.
        traces_by_name.setdefault(name, trace)
        if qualified:
            traces_by_name.setdefault(qualified, trace)
            parts = qualified.split("::")
            for i in range(1, len(parts)):
                traces_by_name.setdefault("::".join(parts[i:]), trace)

    # Pass 2: satisfy relationships (SatisfyRequirementUsage grammar
    # wrappers live inside parts/definitions).
    for obj in _walk(model):
        _extract_satisfy_edges(obj, traces_by_name, traces)

    return TraceabilityReport(requirements=traces)


# ---------------------------------------------------------------------------
# matrix view
# ---------------------------------------------------------------------------


def as_traceability_matrix_view(
    model,
    focus=None,
    elements=None,
    style="bw",
    direction="TB",
    custom_style=None,
    output_format="markdown",
    show_text=False,
):
    """Requirements × traceability-coverage matrix.

    Parameters mirror the other view functions: ``focus`` narrows the
    requirement set (a name or list of names), ``elements`` keeps only
    requirements satisfied by one of the given subjects, ``output_format``
    is one of ``"markdown"`` (default), ``"plantuml"`` or ``"html"``, and
    ``show_text`` includes the requirement documentation column.

    Returns the rendered table as a string.
    """
    report = extract_traceability(model)
    reqs = report.requirements
    if focus is not None:
        focus_names = [focus] if isinstance(focus, str) else list(focus)
        reqs = [
            t for t in reqs
            if t.name in focus_names or t.qualified_name in focus_names
        ]
    if elements:
        element_names = {
            e if isinstance(e, str) else getattr(e, "name", str(e))
            for e in elements
        }
        reqs = [
            t for t in reqs
            if any(s in element_names for s in t.satisfied_by)
        ]

    def _sat(t):
        return ", ".join(t.satisfied_by) or "—"

    def _ver(t):
        return ", ".join(t.verified_by) or "—"

    if output_format == "markdown":
        header = "| Requirement | Status | Satisfied by | Verified by |"
        if show_text:
            header = "| Requirement | Status | Satisfied by | Verified by | Text |"
        sep = "|" + "---|" * (5 if show_text else 4)
        lines = [header, sep]
        for t in reqs:
            name = t.qualified_name or t.name
            cells = [name, t.status, _sat(t), _ver(t)]
            if show_text:
                text = (t.text or "—").replace("|", "\\|")
                cells.append(text)
            lines.append("| " + " | ".join(cells) + " |")
        return "\n".join(lines)

    if output_format == "html":
        rows = []
        for t in reqs:
            text = (t.text or "&mdash;") if show_text else None
            name = t.qualified_name or t.name
            row = (
                f"<tr><td>{name}</td><td>{t.status}</td>"
                f"<td>{_sat(t)}</td><td>{_ver(t)}</td>"
            )
            if show_text:
                row += f"<td>{text}</td>"
            rows.append(row + "</tr>")
        head = (
            "<tr><th>Requirement</th><th>Status</th>"
            "<th>Satisfied by</th><th>Verified by</th>"
        )
        if show_text:
            head += "<th>Text</th>"
        return (
            '<table border="1">\n' + head + "</tr>\n"
            + "\n".join(rows)
            + "\n</table>"
        )

    if output_format == "plantuml":
        lines = ["@startuml", "left to right direction"]
        if style == "color":
            colors = {
                "covered": "#dfffdf",
                "partial": "#fff7df",
                "uncovered": "#ffdfdf",
            }
        else:
            colors = {}
        for t in reqs:
            name = (t.qualified_name or t.name).replace("::", ".")
            rid = f"req_{abs(hash(name)) % 10**8}"
            color = colors.get(t.status, "")
            label = name + (f"\\n{t.text}" if show_text and t.text else "")
            suffix = f" {color}" if color else ""
            lines.append(f'object "{label}" as {rid}{suffix}')
            for s in t.satisfied_by:
                sid = f"sat_{abs(hash(s)) % 10**8}"
                if f'object "{s}" as {sid}' not in lines:
                    lines.append(f'object "{s}" as {sid}')
                lines.append(f"{sid} ..> {rid} : satisfy")
            for v in t.verified_by:
                vid = f"ver_{abs(hash(v)) % 10**8}"
                if f'object "{v}" as {vid}' not in lines:
                    lines.append(f'object "{v}" as {vid}')
                lines.append(f"{vid} ..> {rid} : verify")
        lines.append("@enduml")
        return "\n".join(lines)

    raise ValueError(
        f"Unsupported output_format: {output_format!r} "
        "(expected 'markdown', 'html' or 'plantuml')"
    )