#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compile Grammar

Merges the 3 textX grammar files (KerMLExpressions.tx, KerML.tx, SysML.tx)
into a single flat grammar file (SysML_compiled.tx) for use at runtime.

The compilation process:
1. Reads each .tx file in order: KerMLExpressions, KerML, SysML
2. Strips comments (// and /* */)
3. Extracts individual grammar rules
4. Deduplicates rules (SysML rules override KerML rules of the same name,
   since SysML is read last and prepended to the list)
5. Writes a single flat grammar file

Usage:
    python compile_grammar.py

Run from the textx/ directory or the project root. The script will find
the grammar files relative to its own location.
"""
import os
import re
import sys


def compile_grammar(grammar_dir=None, output_file=None):
    """Compile the 3 .tx files into a single SysML_compiled.tx.

    Parameters
    ----------
    grammar_dir : str, optional
        Path to the grammar directory containing the .tx files.
        Defaults to ../grammar/ relative to this script.
    output_file : str, optional
        Path to the output compiled grammar file.
        Defaults to grammar_dir/SysML_compiled.tx.

    Returns
    -------
    str
        The compiled grammar as a string.
    """
    if grammar_dir is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        grammar_dir = os.path.join(script_dir, "..", "grammar")

    grammar_dir = os.path.abspath(grammar_dir)

    if output_file is None:
        output_file = os.path.join(grammar_dir, "SysML_compiled.tx")

    comments_strip_rule = r"(?:(?:(?<!\\)(\/\/.*\n))|(?:\/\*(?:.|\n)*?\*\/))"
    regex_rule = r"\n[ ]*([\w]*)[ ]*:((?:(?:'[^']*')|(?:[^;']*))*;)"

    g_list = []
    rule_files = ["KerMLExpressions", "KerML", "SysML"]
    for file in rule_files:
        filepath = os.path.join(grammar_dir, file + ".tx")
        print(f"  Reading {filepath}")
        with open(filepath, "r") as f:
            content = f.read()
        # Strip comments, then extract rules
        stripped = re.sub(comments_strip_rule, "", content)
        rules = re.findall(regex_rule, stripped)
        # Prepend so that later files (SysML) take precedence
        g_list = rules + g_list

    # Deduplicate: first occurrence of each rule name wins
    # Since SysML rules are prepended first, they override KerML rules
    seen = set()
    unique_rules = []
    for rule_name, rule_body in g_list:
        if rule_name and rule_name not in seen:
            seen.add(rule_name)
            unique_rules.append((rule_name, rule_body))

    grammar = "\n\n".join([":".join(x) for x in unique_rules])

    print(f"  Writing {output_file}")
    print(f"  Total rules: {len(unique_rules)}")
    with open(output_file, "w") as f:
        f.write(grammar)

    return grammar


if __name__ == "__main__":
    print("Compiling SysML grammar...")
    compile_grammar()
    print("Done.")
