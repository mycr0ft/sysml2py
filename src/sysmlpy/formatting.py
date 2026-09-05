#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed May 31 13:26:53 2023

@author: mycr0ft
"""

from sysmlpy.grammar.classes import RootNamespace


def remove_classes(model):
    """An example docstring for a class definition."""
    if type(model) == type(dict()):
        output = {}
        for element in model:
            if not "_" in element[0] and not "parent" in element:
                # Remove internal parsing elements
                output[element] = remove_classes(model[element])
    elif type(model) == type(list()):
        # List of classes
        output = []
        for member in model:
            output.append(remove_classes(member))
    elif type(model) == type(None):
        return None
    elif type(model) == type(bool()) or type(model) == type(str()):
        return model
    else:
        output = {"name": model.__class__.__name__}
        model_out = remove_classes(model.__dict__)
        output.update(model_out)

    return output


def reformat(model):
    """An example docstring for a class definition."""
    # Convert to dictionary format
    model_out = {"name": model.__class__.__name__}
    model_out.update(remove_classes(model.__dict__))

    return model_out


def classtree(model):
    """Convert a model into a dumpable RootNamespace tree.

    Accepts:
    - a visitor grammar dict (historical input shape, e.g. from
      ``load_grammar(text)``),
    - a public-API ``Model`` from ``loads(text)`` — its ``.grammar``
      is already a ``RootNamespace`` and is returned directly.

    ``tree.dump()`` then renders SysML text.  Passing a ``Model``
    used to raise ``TypeError``; the README/TUTORIAL documented the
    Model form, so it is now supported (v0.78.0).
    """
    if isinstance(model, dict):
        return RootNamespace(model)
    grammar = getattr(model, "grammar", None)
    if grammar is not None and grammar.__class__.__name__ == "RootNamespace":
        return grammar
    return RootNamespace(model)
