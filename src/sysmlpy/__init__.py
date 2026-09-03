#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SysML v2 Python Library

A pure Python implementation for parsing SysML v2.0 models.
Uses the ANTLR4 parser for full SysML v2 grammar support.
"""

__all__ = [
    "load", "loads", "parse", "load_grammar", "load_antlr", "load_grammar_antlr",
    "load_files", "load_project", "load_with_dependencies",
    "Searchable",
    "Store", "InMemoryStore", "NetworkXStore", "KuzuStore", "CayleyStore", "create_store", "new_id",
    "to_plantuml", "PlantUMLGenerator",
    "as_action_flow_view", "as_interconnection_view", "as_state_transition_view",
    "as_general_view", "as_package_view",
    "as_tabular_view", "as_data_value_tabular_view", "as_relationship_matrix_view",
    "as_traceability_matrix_view",
    "as_sequence_view", "as_case_view", "as_browser_view",
    "extract_traceability", "TraceabilityReport", "RequirementTrace",
    "to_interchange", "from_interchange", "interchange_to_json_text",
    "evaluate_expression", "evaluate_calculation", "collect_values",
    "check_constraints", "ConstraintReport", "ConstraintResult",
    "tabular_view_to_csv", "data_value_tabular_to_csv",
    "relationship_matrix_to_csv", "write_xlsx",
    "import_values_csv", "import_values_xlsx", "parse_value_literal",
    "analyze", "AnalysisResult", "SemanticIssue", "SemanticAnalyzer",
    "SysMLSyntaxError", "PartialParseError",
    "loads_partial", "load_partial",
    # boxes-backed optional renderers (require pip install -e ../boxes)
    "as_state_transition_view_boxes", "render_state_transition_view",
    "render_state_transition_view_svg", "boxes_view",
]
__author__ = "Jon Fox"
__version__ = "0.66.0"

from sysmlpy.usage import (
    Item, Attribute, Part, Port, Action, Reference, UseCase, Requirement, Interface, Message,
    State, Constraint, Connection, Flow, Calculation, Enumeration,
    Allocation, Metadata, Rendering, Individual, FlowDef,
    View, Viewpoint, Concern,
    Case, AnalysisCase, VerificationCase, Dependency,
)

from sysmlpy.definition import Model, Package
from sysmlpy.navigate import Searchable
from sysmlpy.store import Store, InMemoryStore, NetworkXStore, KuzuStore, CayleyStore, create_store, new_id

from sysmlpy.usage import ureg
from sysmlpy.antlr_parser import SysMLSyntaxError
from sysmlpy.traceability import (
    extract_traceability, TraceabilityReport, RequirementTrace,
    as_traceability_matrix_view,
)
from sysmlpy.interchange import (
    to_interchange, from_interchange, interchange_to_json_text,
)
from sysmlpy.evaluator import (
    evaluate_expression, evaluate_calculation, collect_values,
    check_constraints, ConstraintReport, ConstraintResult,
)
from sysmlpy.spreadsheet import (
    tabular_view_to_csv, data_value_tabular_to_csv,
    relationship_matrix_to_csv, write_xlsx,
    import_values_csv, import_values_xlsx, parse_value_literal,
)


class PartialParseError(Exception):
    """Raised by ``loads_partial`` / ``load_partial`` when the source has
    syntax errors but at least one construct parsed successfully.

    Attributes
    ----------
    errors : list[str]
        ANTLR-style error messages collected during parsing.
    partial : dict | None
        Visitor dict for whatever did parse (``None`` if nothing did).
    source : str
        The original SysML source (helpful for tooling that wants to
        serialize the partial result back to a file).
    """

    def __init__(self, errors, partial, source):
        self.errors = list(errors)
        self.partial = partial
        self.source = source
        super().__init__(
            f"partial parse: {len(self.errors)} error(s); "
            f"partial={'available' if partial is not None else 'empty'}"
        )


def load_grammar(s, debug=False):
    """SysML load from string to dictionary

    Deserialize a string containing a SysML v2.0 document to a Python dictionary.

    Parameters
    ----------
    s : str or _io.TextIOWrapper
        String instance of SysML v2.0 document or file pointer

    Returns
    -------
    dict
        Dictionary version structured utilizing SysML v2.0 grammar

    Raises
    ------
    TypeError
        Input was not str or file
    """
    import sysmlpy.antlr_visitor as antlr_visitor
    import sysmlpy.antlr_parser as antlr_parser
    import io

    # Handle file pointer or string
    if isinstance(s, io.TextIOWrapper):
        s = s.read()
    elif not isinstance(s, str):
        raise TypeError(
            f"the SysML object must be str or file, not {s.__class__.__name__}"
        )

    # Wrap in package if not starting with 'package' for parsing
    s_stripped = s.strip()
    needs_unwrap = not s_stripped.startswith('package')
    if needs_unwrap:
        # Ensure the implicit closing brace cannot be swallowed by a
        # trailing line comment without a terminating newline.
        if not s_stripped.endswith('\n'):
            s_stripped += '\n'
        s = f'package __implicit__ {{ {s_stripped} }}'

    try:
        result = antlr_visitor.parse_to_dict(s)
        
        # If we wrapped, we need to return a format compatible with what the tests expect
        # The grammar classes expect "PackageBodyElement" as the top-level name
        if needs_unwrap:
            # Navigate to Package body ownedRelationship
            pkg_member = result['ownedRelationship'][0]
            pkg_elem = pkg_member['ownedRelatedElement']
            pkg = pkg_elem['ownedRelatedElement']
            body = pkg['body']
            
            # Return in PackageBodyElement format (no Package wrapper)
            return {
                "name": "PackageBodyElement",
                "ownedRelationship": body['ownedRelationship']
            }
        
        return result
    except antlr_parser.SysMLSyntaxError as e:
        raise


def _parse_with_recovery(source):
    """Shared partial-recovery parse used by the ``_partial`` helpers.

    Returns ``(dict_or_None, errors)``. On a fully clean parse the error
    list is empty and the dict is the full visitor output (matching what
    ``load_grammar`` returns on the success path).
    """
    import io
    import sysmlpy.antlr_parser as antlr_parser
    import sysmlpy.antlr_visitor as antlr_visitor

    if hasattr(source, "read"):
        text = source.read()
    elif not isinstance(source, str):
        raise TypeError(
            f"the SysML object must be str or file, not {source.__class__.__name__}"
        )
    else:
        text = source

    s_stripped = text.strip()
    needs_unwrap = not s_stripped.startswith("package")
    if needs_unwrap:
        if not s_stripped.endswith("\n"):
            s_stripped += "\n"
        wrapped = f"package __implicit__ {{ {s_stripped} }}"
    else:
        wrapped = text

    tree, errors = antlr_parser.parse(wrapped, recover=True)
    if tree is None:
        return None, errors
    result = antlr_visitor._visit_root_namespace_dict(tree)
    if needs_unwrap and isinstance(result, dict):
        try:
            pkg_member = result["ownedRelationship"][0]
            pkg_elem = pkg_member["ownedRelatedElement"]
            pkg = pkg_elem["ownedRelatedElement"]
            body = pkg["body"]
            return {
                "name": "PackageBodyElement",
                "ownedRelationship": body["ownedRelationship"],
            }, errors
        except (KeyError, IndexError, TypeError):
            return result, errors
    return result, errors


def loads_partial(text) -> dict:
    """Parse SysML source and return the visitor dict, raising
    :class:`PartialParseError` instead of :class:`SysMLSyntaxError` when
    the input has syntax errors.

    Use this when you want to recover from partial input — e.g. when
    inspecting a file the spec expects to reject. The exception carries
    the partial dict in ``e.partial`` so callers can still ``classtree``
    and ``dump`` whatever did parse.
    """
    if hasattr(text, "read"):
        source = text.read()
        raw = source
    else:
        source = text
        raw = text
    partial, errors = _parse_with_recovery(source)
    if errors:
        raise PartialParseError(errors, partial, raw)
    return partial


def load_partial(text):
    """Parse SysML source and return the typed :class:`Model`, raising
    :class:`PartialParseError` on syntax errors. The exception carries
    ``e.partial`` so callers can still inspect whatever did parse.

    On full success the returned :class:`Model` behaves identically to
    the one returned by :func:`load`.
    """
    if hasattr(text, "read"):
        source = text.read()
    else:
        source = text
    partial, errors = _parse_with_recovery(source)
    if errors:
        raise PartialParseError(errors, partial, source)
    from sysmlpy.formatting import classtree
    return classtree(partial)


def load(fp) -> Model:
    """SysML load from file pointer

    Deserialize ``fp`` (a ``.read()``-supporting file-like object containing
    a SysML v2.0 document) to a Model object.

    Parameters
    ----------
    fp : _io.TextIOWrapper
        File pointer to SysML v2.0 document

    Returns
    -------
    Model
        Model instance structured utilizing SysML v2.0 grammar

    Raises
    ------
    TypeError
        Input was not _io.TextIOWrapper
    """
    import io

    if not isinstance(fp, io.TextIOWrapper):
        raise TypeError(
            f"the SysML object must be _io.TextIOWrapper, "
            f"not {fp.__class__.__name__}"
        )

    return loads(fp.read())


def loads(s: str, library=None) -> Model:
    """Loads a model from string.

    This shortcut function allows a user to build a model from a string by
    first instantiating a base model class which builds out a default namespace
    and then that model loads all elements underneath.

    Uses the ANTLR4 parser.

    Parameters
    ----------
    s : str
        The SysML v2 source code to parse.
    library : str or Path, optional
        Path to SysML v2 library files for resolving imports.

    Returns
    -------
    Model
        Model instance built from the SysML source.
    """
    return Model().load(s, library=library)


def parse(s: str, library=None):
    """Parse SysML source, returning (model, errors) rather than raising.

    Parameters
    ----------
    s : str
        The SysML v2 source code to parse.
    library : str or Path, optional
        Path to SysML v2 library files for resolving imports.

    Returns
    -------
    tuple[Model | None, list[str]]
        ``(Model, [])`` on success, ``(None, [error_lines])`` on syntax error.
    """
    try:
        return loads(s, library=library), []
    except SysMLSyntaxError as e:
        return None, str(e).splitlines()


def load_grammar_antlr(fp, debug=False, library=None):
    """SysML load from file pointer using ANTLR4 parser.

    Deserialize ``fp`` (a ``.read()``-supporting file-like object containing
    a SysML v2.0 document) or ``s`` (a ``str`` instance containing a SysML
    v2.0 document) to a Python dictionary object using the ANTLR4 parser.

    Parameters
    ----------
    fp : _io.TextIOWrapper or str
        File pointer to SysML v2.0 document or string instance of SysML v2.0
        document
    debug : bool
        Enable debug output.
    library : str or Path, optional
        Path to SysML v2 library files for resolving imports.

    Returns
    -------
    dict
        Dictionary version structured utilizing SysML v2.0 grammar

    Raises
    ------
    TypeError
        Input was not _io.TextIOWrapper or str

    """
    import io
    import sysmlpy.antlr_visitor as antlr_visitor
    import sysmlpy.antlr_parser as antlr_parser

    if isinstance(fp, io.TextIOWrapper):
        s = fp.read()
    elif isinstance(fp, str):
        s = fp
    else:
        raise TypeError(
            f"the SysML object must be _io.TextIOWrapper or str "
            f"not {fp.__class__.__name__}"
        )

    try:
        return antlr_visitor.parse_to_dict(s, library=library)
    except antlr_parser.SysMLSyntaxError as e:
        raise


def load_antlr(fp) -> Model:
    """SysML load from file pointer using ANTLR4 parser.

    Deserialize ``fp`` (a ``.read()``-supporting file-like object containing
    a SysML v2.0 document) to a Model object.

    Parameters
    ----------
    fp : _io.TextIOWrapper
        File pointer to SysML v2.0 document

    Returns
    -------
    Model
        Model instance structured utilizing SysML v2.0 grammar

    Raises
    ------
    TypeError
        Input was not _io.TextIOWrapper
    """
    import io

    if not isinstance(fp, io.TextIOWrapper):
        raise TypeError(
            f"the SysML object must be _io.TextIOWrapper, "
            f"not {fp.__class__.__name__}"
        )

    return loads(fp.read())


from sysmlpy.plantuml import (to_plantuml, PlantUMLGenerator,
    as_action_flow_view, as_interconnection_view, as_state_transition_view,
    as_general_view, as_package_view,
    as_tabular_view, as_data_value_tabular_view, as_relationship_matrix_view,
    as_sequence_view, as_case_view, as_browser_view)

from sysmlpy.semantic import analyze, AnalysisResult, SemanticIssue, SemanticAnalyzer

from sysmlpy.project import load_files, load_project, load_with_dependencies

# Optional boxes-backed state-machine renderer (lazy import on first use so
# `import sysmlpy` works without `boxes` installed). The first call to any of
# the functions below triggers `import sysmlpy.boxes_view`, which itself
# raises ImportError with installation instructions if `boxes` is missing.
def __getattr__(name):
    if name == "boxes_view":
        import sysmlpy.boxes_view as bv
        globals()[name] = bv
        return bv
    if name in ("as_state_transition_view_boxes",
                "render_state_transition_view",
                "render_state_transition_view_svg"):
        from sysmlpy import boxes_view as bv
        fn = getattr(bv, name)
        globals()[name] = fn
        return fn
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

