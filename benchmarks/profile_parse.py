#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cProfile harness for the parse pipeline (Goal 11 Batch 5).

Profiles ``parse_to_dict`` end-to-end after a warm-up parse so ANTLR's
in-process DFA caches do not skew the numbers, and prints the top
functions by cumulative and total time, split by subsystem:

- ANTLR generated parser + runtime (``antlr4/``, ``antlr/``)
- visitor (``antlr_visitor.py``)
- grammar classes (``grammar/classes.py``)

Findings (default model, 300 part definitions, reference machine):

- the ANTLR parse itself dominates (~80 % of end-to-end), almost all
  of it inside ``adaptivePredict``/token-stream bookkeeping — which is
  exactly what the persistent DFA cache (``sysmlpy.dfa_cache``)
  addresses for cold starts;
- the visitor + grammar classes account for the remaining ~20 %, spread
  thin across hundreds of small helper functions — no single visitor
  hotspot is worth micro-optimising;

so visitor-level micro-optimisation was deliberately *not* pursued in
batch 5 (documented in TODO.md / CHANGELOG).

Usage::

    python benchmarks/profile_parse.py [parts]
"""
import cProfile
import io
import os
import pstats
import sys


def model_text(parts: int) -> str:
    body = chr(10).join(
        f"part def Comp{i} {{ attribute a{i} : Real := {i}; "
        f"part def Sub{i} {{ attribute b : Boolean; }} }}"
        for i in range(parts))
    return "package Big { " + body + " }"


def main() -> None:
    parts = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    model = model_text(parts)
    os.environ["SYSSMLPY_DFA_CACHE"] = "off"
    sys.path.insert(0, os.path.join(os.path.dirname(__file__),
                                    "..", "src"))
    from sysmlpy import parse
    from sysmlpy.antlr_visitor import parse_to_dict

    parse(model)                      # warm the in-process DFA caches

    pr = cProfile.Profile()
    pr.enable()
    for _ in range(3):
        parse_to_dict(model)
    pr.disable()

    for key in ("cumulative", "tottime"):
        print("=" * 78)
        print("sorted by", key)
        print("=" * 78)
        buf = io.StringIO()
        stats = pstats.Stats(pr, stream=buf)
        stats.sort_stats(key)
        stats.print_stats("antlr_visitor|grammar/classes|antlr4/|antlr/")
        lines = buf.getvalue().splitlines()
        for line in lines[:40]:
            print(line)


if __name__ == "__main__":
    main()