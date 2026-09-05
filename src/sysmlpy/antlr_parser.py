#!/usr/bin/env python3
"""
ANTLR4-based SysML v2.0 parser module.

This module provides an alternative parser to textX, using ANTLR4 grammar
generated from the OMG SysML v2 specification (2026-05 release).
"""
import sys
import os
import warnings

from antlr4 import InputStream, CommonTokenStream
from antlr4.atn.PredictionMode import PredictionMode
from antlr4.error.ErrorListener import ErrorListener

from sysmlpy.antlr.SysMLv2Lexer import SysMLv2Lexer
from sysmlpy.antlr.SysMLv2Parser import SysMLv2Parser


class SysMLSyntaxError(Exception):
    """Exception raised for SysML syntax errors."""
    pass


class ANTLRErrorListener(ErrorListener):
    """Custom error listener for ANTLR parsing errors."""
    
    def __init__(self):
        self.errors = []
    
    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        self.errors.append(f"Syntax error at {line}:{column}: {msg}")
    
    def reportAmbiguity(self, recognizer, dfa, startIndex, stopIndex, exact, ambigAlts, configs):
        pass
    
    def reportAttemptingFullContext(self, recognizer, dfa, startIndex, stopIndex, conflictingAlts, configs):
        pass
    
    def reportContextSensitivity(self, recognizer, dfa, startIndex, stopIndex, prediction, configs):
        pass


def _make_parser(content):
    """Build a lexer/parser pair (with our error listener attached)."""
    input_stream = InputStream(content)
    lexer = SysMLv2Lexer(input_stream)
    lexer.removeErrorListeners()
    token_stream = CommonTokenStream(lexer)
    parser = SysMLv2Parser(token_stream)
    parser.removeErrorListeners()
    return lexer, token_stream, parser


def parse(source, library=None, recover=False, prediction_mode="sll",
          rescue_language="English"):
    """Parse SysML v2.0 source and return a parse tree.

    Uses two-stage parsing by default (v0.56.0): a fast SLL prediction
    pass first, falling back to the full LL pass only when the SLL pass
    reports syntax errors.  This substantially accelerates large models
    (10k+ elements) while producing identical trees for valid input.

    Parameters
    ----------
    source : str or file-like
        Either a string containing SysML v2.0 code, or a file object.
    library : str or Path, optional
        Path to SysML v2 library files for resolving imports.
    recover : bool, default False
        When True, ANTLR's error recovery is used and ``(tree, errors)``
        is returned instead of raising.  ``tree`` may be ``None`` if
        nothing parsed.  When False (default), the function raises
        :class:`SysMLSyntaxError` on syntax errors, preserving the
        historical strict behavior.
    prediction_mode : {"sll", "ll"}, default "sll"
        ``"sll"`` (default) runs the fast SLL pass with LL fallback.
        ``"ll"`` forces the full-context pass directly (slower; useful
        for debugging).  ``"sll_only"`` keeps every pass in SLL
        prediction — including the fallback pass — so diagnostics
        reflect SLL behaviour (error parity with the fast path).
    rescue_language : str, default "English"
        Language tag used when a constraint body that does not parse as
        SysML/KerML is salvaged as a textual representation
        (``rep language "..." /* body */``) instead of failing the whole
        model load (v0.80.0).

    Returns
    -------
    ParseTree, or (ParseTree, list[str]) when recover=True
        The ANTLR4 parse tree (PackageContext) — or a (tree, errors) tuple.

    Raises
    ------
    SysMLSyntaxError
        If ``recover`` is False and the source contains syntax errors
        (after both parse stages).
    """
    from pathlib import Path

    # Handle string or file input
    if hasattr(source, 'read'):
        content = source.read()
    else:
        content = source

    try:
        return _parse_tree(content, recover=recover,
                           prediction_mode=prediction_mode)
    except SysMLSyntaxError as original_error:
        if recover or not rescue_language:
            raise
        # Constraint-body rescue (v0.80.0): a constraint whose body does
        # not parse as SysML/KerML (e.g. natural-language text) fails the
        # whole model.  Salvage such bodies as language-tagged textual
        # representations and retry once.
        rescued = _rescue_constraint_bodies(content, rescue_language)
        if rescued is None:
            raise
        new_content, rescued_names, rescued_language = rescued
        try:
            tree = _parse_tree(new_content, recover=False,
                               prediction_mode=prediction_mode)
        except SysMLSyntaxError:
            # Rescue did not make the model parseable (e.g. other errors
            # elsewhere) — surface the original diagnostics.
            raise original_error
        for cname in rescued_names:
            warnings.warn(
                f"constraint {cname!r} body did not parse as SysML; captured "
                f"as textual representation (language {rescued_language!r})",
                stacklevel=3,
            )
        return tree


def _parse_tree(content, recover=False, prediction_mode="sll"):
    """Two-stage ANTLR parse (no rescue); the body of historical parse()."""
    force_ll = prediction_mode == "ll"
    sll_only = prediction_mode == "sll_only" or force_ll

    # Persistent DFA cache (v0.84.0): reinstate the prediction caches
    # warmed by previous processes before the first parse of this one.
    from sysmlpy import dfa_cache as _dfa_cache
    _dfa_cache.maybe_load()
    
    if not force_ll:
        # ── Stage 1: SLL fast-path ────────────────────────────────────
        lexer, token_stream, parser = _make_parser(content)
        error_listener = ANTLRErrorListener()
        lexer.addErrorListener(error_listener)
        parser.addErrorListener(error_listener)
        parser._interp.predictionMode = PredictionMode.SLL
        # Bail-out strategy: abort as soon as an SLL conflict is found —
        # any error means we redo the whole parse in LL mode.
        from antlr4.error.ErrorStrategy import BailErrorStrategy
        tree = None
        sll_errors = []
        try:
            parser._errHandler = BailErrorStrategy()
            tree = parser.rootNamespace()
        except Exception:
            tree = None
            sll_errors = ["<sll>"]
        if tree is not None and not error_listener.errors:
            # ── fast path succeeded ──────────────────────────────────
            _maybe_save_dfa_cache()
            if recover:
                return tree, []
            return tree
        if sll_only:
            # Caller forced SLL-only; fall through with the collected
            # errors but re-run without bail to build the partial tree.
            pass

    # ── Stage 2: full parse (fallback / forced mode) ──────────────────
    lexer, token_stream, parser = _make_parser(content)
    error_listener = ANTLRErrorListener()
    lexer.addErrorListener(error_listener)
    parser.addErrorListener(error_listener)
    from antlr4.error.ErrorStrategy import DefaultErrorStrategy
    parser._errHandler = DefaultErrorStrategy()
    # SLL error parity (Goal 10): an explicit "sll_only" request stays
    # in SLL prediction so its diagnostics match the fast pass; every
    # other fallback (sll -> ll, forced ll) uses full LL prediction.
    if prediction_mode == "sll_only":
        parser._interp.predictionMode = PredictionMode.SLL
    else:
        parser._interp.predictionMode = PredictionMode.LL
    tree = parser.rootNamespace()

    # Check for errors
    if error_listener.errors:
        if recover:
            _maybe_save_dfa_cache()
            return tree, error_listener.errors
        raise SysMLSyntaxError("\n".join(error_listener.errors))

    _maybe_save_dfa_cache()
    if recover:
        return tree, []

    return tree


def _maybe_save_dfa_cache():
    """Persist the warmed DFA cache once per process (never fatal)."""
    try:
        from sysmlpy import dfa_cache
        dfa_cache.maybe_save()
    except Exception:
        pass


def _rescue_constraint_bodies(content, language="English"):
    """Salvage constraint bodies that do not parse as SysML/KerML.

    Scans the source for ``constraint ... { ... }`` blocks, trial-parses
    each body, and wraps failing ones as language-tagged textual
    representations (``rep language "..." /* body */``) so a
    natural-language constraint no longer fails the whole model load.

    Returns ``(new_content, [constraint names], language)`` when at least
    one body was rewritten, ``None`` when nothing was salvageable.

    Constraints whose body contains ``*/`` cannot be wrapped in a comment
    and are left untouched (the original error stands).
    """
    import re as _re

    spans = []
    try:
        lexer = SysMLv2Lexer(InputStream(content))
        lexer.removeErrorListeners()
        tokens = CommonTokenStream(lexer)
        tokens.fill()
    except Exception:
        return None
    toks = [t for t in tokens.tokens if t.channel == 0]
    n = len(toks)
    i = 0
    while i < n:
        t = toks[i]
        if t.type != SysMLv2Parser.CONSTRAINT:
            i += 1
            continue
        # Walk forward to the opening brace of the body (or bail on ';').
        j = i + 1
        name = None
        lbrace = None
        while j < n:
            tt = toks[j]
            if tt.type == SysMLv2Parser.LBRACE:
                lbrace = j
                break
            if tt.type in (SysMLv2Parser.SEMI, SysMLv2Parser.RBRACE,
                           SysMLv2Parser.EOF):
                break
            if name is None and tt.type != SysMLv2Parser.DEF:
                name = tt.text
            j += 1
        if lbrace is None:
            i += 1
            continue
        # Brace-match the body (token stream already excludes comments).
        depth = 0
        k = lbrace
        while k < n:
            if toks[k].type == SysMLv2Parser.LBRACE:
                depth += 1
            elif toks[k].type == SysMLv2Parser.RBRACE:
                depth -= 1
                if depth == 0:
                    break
            k += 1
        if k >= n or depth != 0:
            i += 1
            continue
        if k > lbrace + 1:
            start = toks[lbrace + 1].start
            end = toks[k - 1].stop
            body_text = content[start:end + 1]
        else:
            body_text = ""
            start = end = toks[lbrace].stop + 1
        if body_text.strip():
            spans.append((name or "?", start, end, body_text))
        i = k + 1

    if not spans:
        return None

    # Trial-parse every body first; rewrite only the ones that fail.
    # Apply the replacements right-to-left so earlier offsets stay valid.
    replacements = []
    rescued_names = []
    for cname, start, end, body_text in spans:
        stripped = body_text.strip()
        if not stripped or "*/" in stripped:
            continue
        probe = ("package __rescue_probe__ { constraint __c__ { "
                 + stripped + " } }")
        try:
            _parse_tree(probe)
            continue  # body is valid SysML — leave it alone
        except SysMLSyntaxError:
            pass
        replacements.append((start, end, stripped))
        rescued_names.append(cname)
    if not rescued_names:
        return None
    for start, end, replacement in sorted(replacements, reverse=True):
        wrapped = 'rep language "%s" /*%s*/' % (language, replacement)
        content = content[:start] + wrapped + content[end + 1:]
    return content, rescued_names, language


def parse_file(filepath):
    """Parse a SysML v2.0 file.
    
    Parameters
    ----------
    filepath : str
        Path to the SysML v2.0 file.
    
    Returns
    -------
    ParseTree
        The ANTLR4 parse tree.
    
    Raises
    ------
    SysMLSyntaxError
        If the file contains syntax errors.
    FileNotFoundError
        If the file does not exist.
    """
    with open(filepath, 'r') as f:
        return parse(f)


def parse_to_json(source):
    """Parse SysML v2.0 source and return JSON-serializable structure.
    
    Parameters
    ----------
    source : str or file-like
        Either a string containing SysML v2.0 code, or a file object.
    
    Returns
    -------
    dict
        A dictionary representation of the parse tree.
    """
    tree = parse(source)
    return parse_tree_to_dict(tree)


def parse_tree_to_dict(tree, include_text=False):
    """Convert a parse tree to a dictionary.
    
    Parameters
    ----------
    tree : ParseTree
        The ANTLR4 parse tree.
    include_text : bool
        Whether to include the text of each node.
    
    Returns
    -------
    dict
        A dictionary representation of the parse tree.
    """
    result = {
        'type': tree.__class__.__name__,
    }
    
    if include_text:
        result['text'] = tree.getText()
    
    # Get children
    for i in range(tree.getChildCount()):
        child = tree.getChild(i)
        child_class = child.__class__.__name__
        
        # Skip terminal nodes (Token) unless requested
        if hasattr(child, 'getSymbol'):
            # This is a terminal node
            if include_text:
                result[f'child_{i}'] = {
                    'type': child_class,
                    'text': child.getText()
                }
        else:
            # This is a rule context
            result[f'child_{i}'] = parse_tree_to_dict(child, include_text)
    
    return result


__all__ = ['parse', 'parse_file', 'parse_to_json', 'SysMLSyntaxError']