#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Command line interface for sysmlpy.

Subcommands
-----------
parse     Parse a SysML file and print a representation (default: repr()).
analyze   Run semantic analysis on one or more files; CI-friendly exit codes.
view      Render a PlantUML / Markdown / HTML view of a model.
format    Canonicalize (pretty-print) SysML files (alias: fmt).

Exit codes
----------
0  success (for analyze: no issues at the --fail-on threshold)
1  findings at or above the failure threshold (analyze) or an
   operational error such as an unknown focus element (view) /
   unformatted file (format --check)
2  parse or load failure, or usage error

Legacy flat invocation (``sysmlpy FILE --dump`` etc.) is preserved for
backward compatibility and behaves exactly like ``sysmlpy parse``.
"""

import argparse
import inspect
import json
import sys
from pathlib import Path

import sysmlpy
from sysmlpy import loads

# Subcommand table, also used to detect the legacy flat invocation form.
SUBCOMMANDS = ("parse", "analyze", "view", "trace", "export", "import",
               "eval", "xlsx", "sim", "format", "fmt")


# ---------------------------------------------------------------------------
# shared helpers
# ---------------------------------------------------------------------------

def _read_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        sys.exit(2)


def _missing_files(paths: list[Path]) -> list[Path]:
    return [p for p in paths if not p.exists()]


def _load_model(files: list[Path], library: str | None):
    """Load one or more SysML files into a single Model.

    Returns ``(model, error_message)``; ``error_message`` is None on
    success.  Uses :func:`sysmlpy.load_files` so multi-file projects are
    merged (same-named packages share a namespace).
    """
    from sysmlpy import load_files

    paths = [str(f) for f in files]
    try:
        model = sysmlpy.load_files(paths, library=library)
        return model, None
    except Exception as e:  # SysMLSyntaxError and any parse-time failure
        return None, str(e)


# ---------------------------------------------------------------------------
# sysmlpy parse
# ---------------------------------------------------------------------------

def cmd_parse(args) -> int:
    file_path = Path(args.file)
    missing = _missing_files([file_path])
    if missing:
        print(f"Error: File '{missing[0]}' not found.", file=sys.stderr)
        return 2
    content = file_path.read_text(encoding="utf-8")

    try:
        model = sysmlpy.loads(content, library=args.library)
    except Exception as e:
        print(f"Error parsing SysML file: {e}", file=sys.stderr)
        return 2

    if args.json:
        from sysmlpy import load_grammar
        grammar_dict = sysmlpy.load_grammar(content)
        print(json.dumps(grammar_dict, indent=2))
    elif args.dump:
        print(model.dump())
    else:
        # Default or --python flag: show repr()
        print(repr(model))
    return 0


# ---------------------------------------------------------------------------
# sysmlpy analyze
# ---------------------------------------------------------------------------

def cmd_analyze(args) -> int:
    from sysmlpy import analyze

    paths = [Path(f) for f in args.files]
    for p in _missing_files(paths):
        print(f"Error: File '{p}' not found.", file=sys.stderr)
        return 2

    model, error = _load_model(paths, args.library)
    if model is None:
        print(f"Parse error: {error}", file=sys.stderr)
        return 2

    result = analyze(model)
    errors = [i for i in result if i.severity == "error"]
    warnings = [i for i in result if i.severity == "warning"]

    if args.format == "json":
        print(json.dumps({
            "files": [str(p) for p in paths],
            "issues": [
                {
                    "severity": i.severity,
                    "code": i.code,
                    "message": i.message,
                    "reference": i.reference,
                }
                for i in result
            ],
            "summary": {"errors": len(errors), "warnings": len(warnings)},
        }, indent=2))
    else:
        shown = list(result)
        if args.no_warnings:
            shown = [i for i in shown if i.severity != "warning"]
        for issue in shown:
            prefix = "error" if issue.severity == "error" else "warning"
            ref = f" [ref: {issue.reference}]" if issue.reference else ""
            print(f"{prefix}: {issue.code}: {issue.message}{ref}")
        if not args.no_summary and shown:
            print(
                f"\n{len(errors)} error(s), {len(warnings)} warning(s) "
                f"in {', '.join(str(p) for p in paths)}"
            )

    if args.fail_on == "never":
        return 0
    threshold = "error" if args.fail_on == "error" else "warning"
    if threshold == "warning":
        return 1 if (errors or warnings) else 0
    return 1 if errors else 0


# ---------------------------------------------------------------------------
# sysmlpy view
# ---------------------------------------------------------------------------

# view short name -> (view function, supports output_format)
VIEW_TABLE = {
    "gv": "as_general_view",                    # General View
    "pv": "as_package_view",                    # Package View
    "afv": "as_action_flow_view",               # ActionFlowView
    "iv": "as_interconnection_view",            # InterconnectionView
    "stv": "as_state_transition_view",          # StateTransitionView
    "sv": "as_sequence_view",                   # Sequence View
    "cv": "as_case_view",                       # Case View
    "tabular": "as_tabular_view",               # GridView (Tabular)
    "datavalue": "as_data_value_tabular_view",  # Data Value Tabular
    "matrix": "as_relationship_matrix_view",    # Relationship Matrix
    "browser": "as_browser_view",               # Browser (tree) view
}


def cmd_view(args) -> int:
    func_name = VIEW_TABLE[args.view]
    view_func = getattr(sysmlpy, func_name)

    file_path = Path(args.file)
    missing = _missing_files([file_path])
    if missing:
        print(f"Error: File '{missing[0]}' not found.", file=sys.stderr)
        return 2
    content = file_path.read_text(encoding="utf-8")

    try:
        model = sysmlpy.loads(content, library=args.library)
    except Exception as e:
        print(f"Parse error: {e}", file=sys.stderr)
        return 2

    # Focus must name an existing element, so a typo fails loudly instead
    # of silently rendering the whole model.
    if args.focus is not None:
        try:
            found = model.find_one(args.focus)
        except LookupError as e:
            print(f"Error: --focus '{args.focus}': {e}", file=sys.stderr)
            return 1
        if found is None:
            print(
                f"Error: --focus '{args.focus}': no element with that name",
                file=sys.stderr,
            )
            return 1

    # Only pass keyword arguments the view function actually accepts.
    kwargs = {}
    sig = inspect.signature(view_func)
    if "focus" in sig.parameters and args.focus is not None:
        kwargs["focus"] = args.focus
    if "elements" in sig.parameters and args.elements:
        kwargs["elements"] = args.elements
    if "style" in sig.parameters:
        kwargs["style"] = args.style
    if "direction" in sig.parameters and args.direction:
        kwargs["direction"] = args.direction
    if "output_format" in sig.parameters and args.format:
        kwargs["output_format"] = args.format

    try:
        output = view_func(model, **kwargs)
    except LookupError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(
            f"Error: view '{args.view}' failed on this model: "
            f"{type(e).__name__}: {e}",
            file=sys.stderr,
        )
        return 1

    if args.output:
        Path(args.output).write_text(str(output), encoding="utf-8")
        print(f"Wrote {args.output}")
    else:
        print(output)
    return 0


# ---------------------------------------------------------------------------
# sysmlpy format
# ---------------------------------------------------------------------------

def cmd_format(args) -> int:
    paths = [Path(f) for f in args.files]
    missing = _missing_files(paths)
    if missing:
        for p in missing:
            print(f"Error: File '{p}' not found.", file=sys.stderr)
        return 2

    exit_code = 0
    for file_path in paths:
        content = file_path.read_text(encoding="utf-8")
        try:
            model = sysmlpy.loads(content, library=args.library)
        except Exception as e:
            print(f"Error parsing SysML file '{file_path}': {e}", file=sys.stderr)
            exit_code = 2
            continue

        formatted = model.dump()
        if args.check:
            if formatted != content:
                print(f"{file_path} would be reformatted")
                exit_code = 1
        elif args.in_place:
            if formatted != content:
                file_path.write_text(formatted, encoding="utf-8")
                print(f"Formatted {file_path}")
        else:
            print(formatted)
    return exit_code


def cmd_trace(args) -> int:
    """Requirement traceability & verification coverage (v0.62.0, Goal 2)."""
    from sysmlpy.traceability import extract_traceability

    paths = [Path(f) for f in args.files]
    for p in _missing_files(paths):
        print(f"Error: File '{p}' not found.", file=sys.stderr)
        return 2

    try:
        model = sysmlpy.load_files(paths, library=args.library)
    except Exception as e:
        print(f"Parse error: {e}", file=sys.stderr)
        return 2

    report = extract_traceability(model)

    if args.format == "json":
        output = json.dumps(report.to_json(), indent=2)
    elif args.format == "markdown":
        output = report.to_markdown()
    else:
        output = report.to_text()

    if args.output:
        Path(args.output).write_text(output + "\n", encoding="utf-8")
        print(f"Wrote {args.output}")
    else:
        print(output)

    if args.fail_on == "uncovered" and report.uncovered():
        for trace in report.uncovered():
            print(
                f"uncovered: {trace.qualified_name or trace.name}",
                file=sys.stderr,
            )
        return 1
    return 0


def cmd_export(args) -> int:
    """SysML text → JSON interchange document (v0.63.0, Goal 3)."""
    from sysmlpy.interchange import to_interchange, interchange_to_json_text

    paths = [Path(f) for f in args.files]
    for p in _missing_files(paths):
        print(f"Error: File '{p}' not found.", file=sys.stderr)
        return 2

    try:
        model = sysmlpy.load_files(paths, library=args.library)
    except Exception as e:
        print(f"Parse error: {e}", file=sys.stderr)
        return 2

    try:
        document = to_interchange(model)
    except Exception as e:
        print(f"Error: export failed on this model: {e}", file=sys.stderr)
        return 1

    output = interchange_to_json_text(document, indent=None if args.compact else 2)
    if args.output:
        Path(args.output).write_text(output + "\n", encoding="utf-8")
        print(f"Wrote {args.output}")
    else:
        print(output)
    return 0


def cmd_import(args) -> int:
    """JSON interchange document → SysML text (v0.63.0, Goal 3)."""
    from sysmlpy.interchange import from_interchange

    path = Path(args.file)
    if not path.exists():
        print(f"Error: File '{path}' not found.", file=sys.stderr)
        return 2

    try:
        content = path.read_text(encoding="utf-8")
    except OSError as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        return 2

    try:
        model = from_interchange(content)
    except ValueError as e:
        print(f"Error: invalid interchange document: {e}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as e:
        print(f"Error: not valid JSON: {e}", file=sys.stderr)
        return 2

    output = model.dump()
    if args.output:
        if not output.endswith("\n"):
            output += "\n"
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Wrote {args.output}")
    else:
        print(output)
    return 0


def _parse_eval_value(text):
    """Parse a --set NAME=VALUE literal (number / bool / string / unit)."""
    from sysmlpy.usage import ureg
    raw = text
    low = raw.strip().lower()
    if low == "true":
        return True
    if low == "false":
        return False
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    try:
        return ureg(raw)
    except Exception:
        pass
    return raw


def cmd_eval(args) -> int:
    """Expression evaluation / constraint checking (v0.64.0, Goal 4)."""
    from sysmlpy.evaluator import (
        evaluate_expression, collect_values, check_constraints,
        EvaluationError,
    )

    paths = [Path(f) for f in args.files]
    for p in _missing_files(paths):
        print(f"Error: File '{p}' not found.", file=sys.stderr)
        return 2

    try:
        model = sysmlpy.load_files(paths, library=args.library)
    except Exception as e:
        print(f"Parse error: {e}", file=sys.stderr)
        return 2

    bindings = {}
    for spec in args.set or []:
        if "=" not in spec:
            print(f"Error: --set expects NAME=VALUE, got {spec!r}",
                  file=sys.stderr)
            return 2
        name, _, raw = spec.partition("=")
        bindings[name.strip()] = _parse_eval_value(raw)

    if getattr(args, "set_file", None):
        from sysmlpy.spreadsheet import import_values_csv, import_values_xlsx
        setfile = Path(args.set_file)
        if not setfile.exists():
            print(f"Error: --set-file '{setfile}' not found.", file=sys.stderr)
            return 2
        try:
            if setfile.suffix.lower() == ".xlsx":
                file_bindings = import_values_xlsx(setfile)
            else:
                # utf-8-sig tolerates Excel's BOM on CSV exports
                file_bindings = import_values_csv(
                    setfile.read_text(encoding="utf-8-sig")
                )
        except (ValueError, ImportError, OSError) as e:
            print(f"Error: --set-file: {e}", file=sys.stderr)
            return 1
        # --set flags win over spreadsheet values
        bindings = {**file_bindings, **bindings}

    if args.expr is not None:
        try:
            value = evaluate_expression(
                args.expr, model=model, element=args.element,
                bindings=bindings,
            )
        except EvaluationError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        print(_format_value(value))
        return 0

    if args.constraints:
        report = check_constraints(model, bindings=bindings)
        output = report.to_text()
        if args.output:
            Path(args.output).write_text(output + "\n", encoding="utf-8")
            print(f"Wrote {args.output}")
        else:
            print(output)
        if report.failed or report.errored:
            return 1
        return 0

    # default: dump all attribute values
    values = collect_values(model, bindings=bindings)
    lines = [f"{name} = {_format_value(value)}"
             for name, value in sorted(values.items())]
    output = "\n".join(lines) if lines else "(no attribute values)"
    if args.output:
        Path(args.output).write_text(output + "\n", encoding="utf-8")
        print(f"Wrote {args.output}")
    else:
        print(output)
    return 0


def _format_value(value):
    if isinstance(value, bool):
        return str(value)
    if value is None:
        return "null"
    return str(value)


def cmd_sim(args) -> int:
    """Simulate the state machine of a model (interactive TUI)."""
    try:
        from sysmlpy.sim import run_tui
    except ImportError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    paths = [Path(args.file)]
    for p_ in _missing_files(paths):
        print(f"Error: File '{p_}' not found.", file=sys.stderr)
        return 2
    try:
        model = sysmlpy.load_files(paths, library=args.library)
    except Exception as e:
        print(f"Parse error: {e}", file=sys.stderr)
        return 2

    values = {}
    for spec in args.set or []:
        if "=" not in spec:
            print(f"Error: --set expects NAME=VALUE, got {spec!r}",
                  file=sys.stderr)
            return 2
        name, _, raw = spec.partition("=")
        values[name.strip()] = _parse_eval_value(raw)

    script = [t.strip() for t in (args.run or "").split(";") if t.strip()]
    try:
        from sysmlpy.sim import StateSimulator, SimulationError
        sim = StateSimulator(model, focus=args.focus, values=values)
    except (ImportError, SimulationError) as e:
        print(f"Simulation error: {e}", file=sys.stderr)
        return 2
    for note in sim.notes:
        print(f"note: {note}")
    if script:
        for trigger in script:
            fired = sim.send(trigger)
            print(f"{trigger}: {'fired' if fired else 'blocked'} "
                  f"-> {sim.state!r}")
        return 0
    run_tui(model, focus=args.focus, values=values)
    return 0


def cmd_xlsx(args) -> int:
    """Export tabular views to an Excel workbook (v0.66.0, Goal 7)."""
    from sysmlpy.spreadsheet import write_xlsx

    paths = [Path(f) for f in args.files]
    for p in _missing_files(paths):
        print(f"Error: File '{p}' not found.", file=sys.stderr)
        return 2

    try:
        model = sysmlpy.load_files(paths, library=args.library)
    except Exception as e:
        print(f"Parse error: {e}", file=sys.stderr)
        return 2

    include = tuple(s.strip() for s in args.sheets.split(",") if s.strip())
    try:
        out = write_xlsx(model, args.output, include=include,
                         focus=args.focus)
    except ImportError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: xlsx export failed: {type(e).__name__}: {e}",
              file=sys.stderr)
        return 1
    print(f"Wrote {out}")
    return 0


# ---------------------------------------------------------------------------
# legacy flat invocation (kept for backward compatibility)
# ---------------------------------------------------------------------------

def _legacy_main(args) -> int:
    """Legacy flat behavior, with its original exit codes (1 on errors).

    Returns the exit code instead of calling sys.exit so in-process
    callers can inspect it; the console script wrapper applies it.
    """
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"Error: File '{args.file}' not found.", file=sys.stderr)
        return 1

    try:
        content = file_path.read_text(encoding="utf-8")
    except OSError as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        return 1

    try:
        model = sysmlpy.loads(content, library=args.library)
    except Exception as e:
        print(f"Error parsing SysML file: {e}", file=sys.stderr)
        return 1

    if args.json:
        grammar_dict = sysmlpy.load_grammar(content)
        print(json.dumps(grammar_dict, indent=2))
        return 0

    if args.dump or args.in_place or args.check:
        formatted = model.dump()
        if args.check:
            return 0 if formatted == content else 1
        if args.in_place:
            file_path.write_text(formatted, encoding="utf-8")
            print(f"Formatted {file_path}")
            return 0
        print(formatted)
        return 0

    # Default or --python flag: show repr()
    print(repr(model))
    return 0


# ---------------------------------------------------------------------------
# argument parser assembly
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sysmlpy",
        description=(
            "Parse, analyze, and render SysML v2 models.\n\n"
            "Exit codes: 0 = success / clean, 1 = findings at or above the\n"
            "failure threshold (analyze) or an operational error, 2 = parse\n"
            "or load failure."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version", action="version", version=f"sysmlpy {sysmlpy.__version__}"
    )
    sub = parser.add_subparsers(dest="command")

    # -- parse ---------------------------------------------------------------
    p_parse = sub.add_parser(
        "parse",
        help="Parse a SysML file and print a representation",
        description="Parse a SysML v2 file and display its Python "
                    "representation (default), dumped SysML text (--dump) "
                    "or grammar JSON (--json).",
    )
    p_parse.add_argument("file", help="Path to the SysML v2 file to parse")
    p_parse.add_argument(
        "--python", action="store_true",
        help="Display the Python repr() representation (default)",
    )
    p_parse.add_argument(
        "--dump", action="store_true",
        help="Display the SysML text output (dump format)",
    )
    p_parse.add_argument(
        "--json", action="store_true",
        help="Display the grammar dictionary/JSON representation",
    )
    p_parse.add_argument(
        "-l", "--library",
        help="Path to SysML v2 library files to use for parsing",
    )
    p_parse.set_defaults(func=cmd_parse)

    # -- analyze -------------------------------------------------------------
    p_analyze = sub.add_parser(
        "analyze",
        help="Run semantic analysis; CI-friendly with exit codes",
        description="Load one or more SysML v2 files (merged into a single "
                    "model) and run the semantic analyzer. Exit 0 when "
                    "clean, 1 when issues at or above --fail-on are found, "
                    "2 on parse/load failure.",
    )
    p_analyze.add_argument(
        "files", nargs="+", help="SysML v2 file(s) to analyze"
    )
    p_analyze.add_argument(
        "-l", "--library",
        help="Path to SysML v2 library files to use for parsing",
    )
    p_analyze.add_argument(
        "--format", choices=("text", "json"), default="text",
        help="Output format: human-readable text (default) or JSON",
    )
    p_analyze.add_argument(
        "--fail-on", choices=("error", "warning", "never"), default="error",
        help="Issue severity that causes exit code 1 (default: error)",
    )
    p_analyze.add_argument(
        "--no-warnings", action="store_true",
        help="Suppress warning lines in text output",
    )
    p_analyze.add_argument(
        "--no-summary", action="store_true",
        help="Suppress the trailing error/warning count",
    )
    p_analyze.set_defaults(func=cmd_analyze)

    # -- view ----------------------------------------------------------------
    p_view = sub.add_parser(
        "view",
        help="Render a PlantUML / Markdown / HTML view of a model",
        description="Render one of the sysmlpy views for a SysML file and "
                    "print it (or write it with -o). Graph views (gv, pv, "
                    "afv, iv, stv, sv, cv, browser) emit PlantUML; "
                    "tabular/datavalue/matrix support --format.",
    )
    p_view.add_argument("file", help="SysML v2 file to render")
    p_view.add_argument(
        "--view", required=True, choices=tuple(VIEW_TABLE),
        help="View short name: " + ", ".join(sorted(VIEW_TABLE)),
    )
    p_view.add_argument(
        "-o", "--output",
        help="Write the view to this file instead of stdout",
    )
    p_view.add_argument(
        "--focus",
        help="Element name to focus the view on (renders its subtree)",
    )
    p_view.add_argument(
        "--element", action="append", dest="elements",
        help="Specific element(s) to include (repeatable)",
    )
    p_view.add_argument(
        "--style", choices=("bw", "color"), default="bw",
        help="Diagram style (default: bw)",
    )
    p_view.add_argument(
        "--direction", choices=("TB", "LR"),
        help="Graph direction (graph views only)",
    )
    p_view.add_argument(
        "--format", choices=("plantuml", "markdown", "html", "csv"),
        help="Output format for tabular/datavalue/matrix views "
             "(csv added in v0.66.0)",
    )
    p_view.add_argument(
        "-l", "--library",
        help="Path to SysML v2 library files to use for parsing",
    )
    p_view.set_defaults(func=cmd_view)

    # -- format --------------------------------------------------------------
    p_format = sub.add_parser(
        "format",
        aliases=("fmt",),
        help="Pretty-print (canonicalize) SysML files",
        description="Parse each file and print the canonical dumped text "
                    "to stdout, write it back in place (-i), or verify "
                    "formatting (--check).",
    )
    p_format.add_argument("files", nargs="+", help="SysML v2 file(s)")
    p_format.add_argument(
        "-i", "--in-place", action="store_true",
        help="Rewrite the files with formatted output",
    )
    p_format.add_argument(
        "--check", action="store_true",
        help="Check formatting; exit 1 if a file would be reformatted",
    )
    p_format.add_argument(
        "-l", "--library",
        help="Path to SysML v2 library files to use for parsing",
    )
    p_format.set_defaults(func=cmd_format)

    p_trace = sub.add_parser(
        "trace",
        help="Requirement traceability \u0026 verification coverage report",
        description="Load the files as one merged model, extract satisfy "
                    "and verify relationships, and report requirement "
                    "coverage. Exit codes: 0 clean, 1 uncovered "
                    "requirements (--fail-on uncovered), 2 parse error.",
    )
    p_trace.add_argument("files", nargs="+", help="SysML v2 file(s)")
    p_trace.add_argument(
        "--format", choices=("text", "markdown", "json"), default="text",
        help="Report format (default: text)",
    )
    p_trace.add_argument(
        "--fail-on", choices=("uncovered", "none"), default="none",
        help="Exit 1 when uncovered requirements exist (default: none)",
    )
    p_trace.add_argument(
        "-o", "--output",
        help="Write the report to a file instead of stdout",
    )
    p_trace.add_argument(
        "-l", "--library",
        help="Path to SysML v2 library files to use for parsing",
    )
    p_trace.set_defaults(func=cmd_trace)

    p_export = sub.add_parser(
        "export",
        help="Export SysML to the JSON interchange format",
        description="Load the files as one merged model and emit a "
                    "JSON-LD-style partition interchange document "
                    "(flat @graph of elements with @id/@type). Exit 2 "
                    "on parse failure.",
    )
    p_export.add_argument("files", nargs="+", help="SysML v2 file(s)")
    p_export.add_argument(
        "-o", "--output",
        help="Write the JSON document to a file instead of stdout",
    )
    p_export.add_argument(
        "--compact", action="store_true",
        help="Emit compact JSON (no indentation)",
    )
    p_export.add_argument(
        "-l", "--library",
        help="Path to SysML v2 library files to use for parsing",
    )
    p_export.set_defaults(func=cmd_export)

    p_import = sub.add_parser(
        "import",
        help="Import a JSON interchange document as SysML text",
        description="Rebuild a model from a JSON interchange document "
                    "(sysmlpy export format) and print or write the "
                    "equivalent SysML v2 text. Exit 2 on invalid input.",
    )
    p_import.add_argument("file", help="Interchange JSON file")
    p_import.add_argument(
        "-o", "--output",
        help="Write the SysML text to a file instead of stdout",
    )
    p_import.set_defaults(func=cmd_import)

    p_eval = sub.add_parser(
        "eval",
        help="Evaluate expressions, attribute values and constraints",
        description="Bind pint attribute values and evaluate SysML "
                    "expressions, calc results, or constraint bodies. "
                    "Exit codes: 0 clean, 1 constraint failed / "
                    "evaluation error, 2 parse error.",
    )
    p_eval.add_argument("files", nargs="+", help="SysML v2 file(s)")
    p_eval.add_argument(
        "--expr",
        help="Evaluate this expression against the model scope",
    )
    p_eval.add_argument(
        "--set", action="append", metavar="NAME=VALUE",
        help="Override a name for this evaluation (repeatable; values "
             "may be numbers, true/false, or unit strings like '80 km/h')",
    )
    p_eval.add_argument(
        "--set-file", metavar="FILE",
        help="Load bindings from a CSV/XLSX values file "
             "(v0.66.0; headers: Name,Value[,Unit] or "
             "Element,Attribute,Value[,Unit])",
    )
    p_eval.add_argument(
        "--element",
        help="Qualified element name whose scope to evaluate in",
    )
    p_eval.add_argument(
        "--constraints", action="store_true",
        help="Evaluate all constraint bodies; exit 1 on any failure",
    )
    p_eval.add_argument(
        "-o", "--output",
        help="Write the report/value to a file instead of stdout",
    )
    p_eval.add_argument(
        "-l", "--library",
        help="Path to SysML v2 library files to use for parsing",
    )
    p_eval.set_defaults(func=cmd_eval)

    # -- sim (state-machine simulation, optional 'transitions' extra) -----
    p_sim = sub.add_parser(
        "sim",
        help="Simulate a state machine (guards evaluated for real)",
        description="Cameo-style state-machine simulation: fires "
                    "transitions on triggers, evaluates guards against "
                    "the model's attribute values (plus --set "
                    "overrides), and logs effects. Interactive TUI "
                    "(or a scripted run with --run). Requires the "
                    "'sim' extra: pip install 'sysmlpy[sim]'.",
    )
    p_sim.add_argument("file", help="SysML v2 file with a state machine")
    p_sim.add_argument(
        "--focus",
        help="Name of the state def/state machine to simulate "
             "(default: the first one found)",
    )
    p_sim.add_argument(
        "--set", action="append", metavar="NAME=VALUE",
        help="Starting value for guards (repeatable)",
    )
    p_sim.add_argument(
        "--run", metavar="TRIG1;TRIG2",
        help="Fire this ';'-separated trigger sequence instead of "
             "entering the interactive loop",
    )
    p_sim.add_argument(
        "-l", "--library",
        help="Path to SysML v2 library files to use for parsing",
    )
    p_sim.set_defaults(func=cmd_sim)

    # -- xlsx (v0.66.0, Goal 7) -------------------------------------------------
    p_xlsx = sub.add_parser(
        "xlsx",
        help="Export tabular views to an Excel workbook",
        description="Write the Tabular / DataValues / Matrix views into "
                    "an .xlsx workbook (requires the 'openpyxl' extra: "
                    "pip install 'sysmlpy[xlsx]'). Exit codes: 0 clean, "
                    "1 error, 2 parse error.",
    )
    p_xlsx.add_argument("files", nargs="+", help="SysML v2 file(s)")
    p_xlsx.add_argument(
        "-o", "--output", required=True,
        help="Output .xlsx file path",
    )
    p_xlsx.add_argument(
        "--sheets", default="tabular,data_value,matrix",
        help="Comma-separated sheet selection: tabular,data_value,matrix "
             "(default: all)",
    )
    p_xlsx.add_argument(
        "--focus",
        help="Focus element for the tabular views",
    )
    p_xlsx.add_argument(
        "-l", "--library",
        help="Path to SysML v2 library files to use for parsing",
    )
    p_xlsx.set_defaults(func=cmd_xlsx)

    return parser


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)

    if not argv or argv[0] in ("-h", "--help"):
        parser = build_parser()
        parser.print_help()
        return 0 if argv else 2

    if argv[0] in SUBCOMMANDS or argv[0] == "--version":
        parser = build_parser()
        args = parser.parse_args(argv)
        return args.func(args)

    # Legacy flat form: ``sysmlpy FILE [--dump|--json|-i|--check]`` (also
    # preserves flag-first orders like ``--dump FILE``).
    legacy_parser = argparse.ArgumentParser(
        prog="sysmlpy",
        description="Parse a SysML v2 file and display its representation "
                    "(legacy form of 'sysmlpy parse').",
    )
    legacy_parser.add_argument("file", help="Path to the SysML v2 file")
    legacy_parser.add_argument("--python", action="store_true")
    legacy_parser.add_argument("-l", "--library")
    legacy_parser.add_argument("--dump", action="store_true")
    legacy_parser.add_argument("--json", action="store_true")
    legacy_parser.add_argument("-i", "--in-place", action="store_true")
    legacy_parser.add_argument("--check", action="store_true")
    return _legacy_main(legacy_parser.parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())