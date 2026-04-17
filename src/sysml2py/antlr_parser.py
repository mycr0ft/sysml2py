#!/usr/bin/env python3
"""
ANTLR4-based SysML v2.0 parser module.

This module provides an alternative parser to textX, using ANTLR4 grammar
generated from the OMG SysML v2 specification (2026-03 release).
"""
import sys
import os

from antlr4 import InputStream, CommonTokenStream
from antlr4.error.ErrorListener import ErrorListener

from sysml2py.antlr.SysMLv2Lexer import SysMLv2Lexer
from sysml2py.antlr.SysMLv2Parser import SysMLv2Parser


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


def parse(source):
    """Parse SysML v2.0 source and return a parse tree.
    
    Parameters
    ----------
    source : str or file-like
        Either a string containing SysML v2.0 code, or a file object.
    
    Returns
    -------
    ParseTree
        The ANTLR4 parse tree (PackageContext).
    
    Raises
    ------
    SysMLSyntaxError
        If the source contains syntax errors.
    """
    # Handle string or file input
    if hasattr(source, 'read'):
        content = source.read()
    else:
        content = source
    
    # Create input stream
    input_stream = InputStream(content)
    
    # Create lexer
    lexer = SysMLv2Lexer(input_stream)
    
    # Set up error listener
    error_listener = ANTLRErrorListener()
    lexer.removeErrorListeners()
    lexer.addErrorListener(error_listener)
    
    # Create token stream
    token_stream = CommonTokenStream(lexer)
    
    # Create parser
    parser = SysMLv2Parser(token_stream)
    parser.removeErrorListeners()
    parser.addErrorListener(error_listener)
    
    # Parse the source
    tree = parser.package()
    
    # Check for errors
    if error_listener.errors:
        raise SysMLSyntaxError("\n".join(error_listener.errors))
    
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