#!/usr/bin/env python3
"""
ANTLR4-based SysML v2.0 parser module.

This module provides an alternative parser to textX, using ANTLR4 grammar
generated from the OMG SysML v2 specification (2026-05 release).
"""
import sys
import os

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


def parse(source, library=None, recover=False, prediction_mode="sll"):
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
        for debugging).  ``"sll"`` without fallback can be forced with
        ``prediction_mode="sll_only"``.

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

    force_ll = prediction_mode == "ll"
    sll_only = prediction_mode == "sll_only" or force_ll
    
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
            if recover:
                return tree, []
            return tree
        if sll_only:
            # Caller forced SLL-only; fall through with the collected
            # errors but re-run without bail to build the partial tree.
            pass

    # ── Stage 2: full LL parse (fallback) ─────────────────────────────
    lexer, token_stream, parser = _make_parser(content)
    error_listener = ANTLRErrorListener()
    lexer.addErrorListener(error_listener)
    parser.addErrorListener(error_listener)
    from antlr4.error.ErrorStrategy import DefaultErrorStrategy
    parser._errHandler = DefaultErrorStrategy()
    parser._interp.predictionMode = PredictionMode.LL
    tree = parser.rootNamespace()

    # Check for errors
    if error_listener.errors:
        if recover:
            return tree, error_listener.errors
        raise SysMLSyntaxError("\n".join(error_listener.errors))

    if recover:
        return tree, []

    return tree


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