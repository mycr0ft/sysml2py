"""%%sysml cell magic: parse and accumulate SysML v2 models in IPython/Jupyter.

Load once per notebook:

    %load_ext sysmlpy.ipython_magic

Then write SysML v2 textual notation in `%%sysml` cells:

    %%sysml
    package Vehicle {
        part def Engine {
            attribute fuelRate : Real;
        }
        part def Vehicle {
            part engine : Vehicle::Engine;
        }
    }

The parsed model accumulates across cells into a persistent `Model` exposed in
the notebook namespace as `model` (alias `_sysml`). Re-declaring a package
merges at package-member granularity: a re-declared element (matched by name +
sysml_type) replaces the prior definition; other members are preserved.

Line magics (analogues of the OMG Pilot Implementation kernel commands —
see docs/sysml-magics.md in sysml-copier or the module docstrings):

    %sysml_reset                 discard the session model
    %sysml_list [NAME]           list packages, or find elements by exact name
    %sysml_show NAME [--json]    print the AST rooted at a named element
    %sysml_viz NAME [--view V]   PlantUML view of a named element

Requires the `jupyter` extra: pip install sysmlpy[jupyter]
"""
from __future__ import annotations

from pathlib import Path

from IPython.core.magic import Magics, cell_magic, line_magic, magics_class
from IPython.core.magic_arguments import (
    argument,
    magic_arguments,
    parse_argstring,
)


@magics_class
class SysMLMagics(Magics):
    def __init__(self, shell):
        super().__init__(shell)
        self.model = None  # persistent session Model

    # -- helpers -----------------------------------------------------------
    def _publish(self):
        """(Re-)bind the session model into the user namespace."""
        self.shell.push({"model": self.model, "_sysml": self.model})

    def _analyze(self, model, source: str) -> list[str]:
        """Best-effort semantic diagnostics (analyzer API may vary)."""
        out: list[str] = []
        try:
            from sysmlpy import SemanticAnalyzer

            result = SemanticAnalyzer(model).analyze(source)
            for issue in getattr(result, "issues", []) or []:
                out.append(f"[semantic] [{issue.code}] {issue.message}")
        except Exception:
            pass
        return out

    def _merge(self, model) -> int:
        """Merge freshly parsed packages into the session model.

        Member-granularity merge: within a package of the same name, a
        re-declared element (matched by name+sysml_type) replaces the prior
        definition; other members are preserved. New packages are appended.
        Returns the number of replaced members.
        """
        if self.model is None:
            self.model = model
            return 0
        replaced = 0
        for pkg in getattr(model, "packages", []):
            existing_pkg = next(
                (c for c in self.model.children
                 if getattr(c, "name", None) == pkg.name),
                None,
            )
            if existing_pkg is None:
                self.model.children.append(pkg)
                continue
            for member in getattr(pkg, "children", []):
                key = (getattr(member, "name", None),
                       getattr(member, "sysml_type", None))
                children = existing_pkg.children
                for i, old in enumerate(children):
                    if (getattr(old, "name", None),
                            getattr(old, "sysml_type", None)) == key:
                        children[i] = member
                        replaced += 1
                        break
                else:
                    children.append(member)
        return replaced

    # -- the cell magic ----------------------------------------------------
    @magic_arguments()
    @argument("--reset", action="store_true", help="discard the session model first")
    @argument("--file", default=None, metavar="PATH",
              help="parse SysML from PATH instead of the cell body (use '-' as the body)")
    @argument("--show", action="store_true",
              help="print the round-tripped model text after merge")
    @cell_magic
    def sysml(self, line: str, cell: str):
        """Parse a cell of SysML v2 textual notation into the session model."""
        import sys

        args = parse_argstring(self.sysml, line)

        if args.reset:
            self.model = None

        if args.file:
            source = Path(args.file).read_text(encoding="utf-8")
        else:
            source = cell

        from sysmlpy import parse

        model, errors = parse(source)
        if errors:
            for e in errors:
                print(f"[parse] {e}", file=sys.stderr)
            return None

        replaced = self._merge(model)
        for w in self._analyze(model, source):
            print(w, file=sys.stderr)
        self._publish()

        if args.show:
            print(str(self.model))
        total = len(getattr(self.model, "packages", []))
        note = f", {replaced} redefined" if replaced else ""
        print(f"sysml: model updated — {total} package(s) loaded{note}")
        return None

    # -- line magics (OMG kernel command analogues) ------------------------
    @line_magic
    def sysml_reset(self, line: str = ""):
        """%sysml_reset — discard the persistent SysML session model."""
        self.model = None
        self.shell.user_ns.pop("model", None)
        self.shell.user_ns.pop("_sysml", None)
        print("sysml: session model discarded")

    @line_magic
    def sysml_list(self, line: str = ""):
        """%sysml_list [NAME] — list packages, or find elements by exact name.

        Without an argument, lists top-level packages. With a name, lists all
        elements whose declared name matches exactly (any depth). Use
        model.find(sysml_type=...) from Python for richer queries.
        """
        if self.model is None:
            print("sysml: no model loaded — run a %%sysml cell first")
            return None
        name = line.strip() or None
        if name is None:
            for pkg in getattr(self.model, "packages", []):
                print(pkg.name)
            return None
        results = self.model.find(name)
        if not results:
            print(f"sysml: no elements named {name!r}")
        for r in results:
            print(f"{r.sysml_type:14} {r.name}")
        return None

    @magic_arguments()
    @argument("--json", action="store_true",
              help="JSON representation (dump() output piped through json when possible)")
    @argument("name", help="element name (exact declared name)")
    @line_magic
    def sysml_show(self, line: str):
        """%sysml_show NAME [--json] — print the AST rooted at a named element."""
        import json as _json

        args = parse_argstring(self.sysml_show, line)
        if self.model is None:
            print("sysml: no model loaded — run a %%sysml cell first")
            return None
        results = self.model.find(args.name)
        if not results:
            print(f"sysml: no elements named {args.name!r}")
            return None
        for r in results:
            text = r.dump() if hasattr(r, "dump") else str(r)
            if args.json:
                try:
                    parsed = _json.loads(text)
                    print(_json.dumps(parsed, indent=2))
                except (_json.JSONDecodeError, TypeError):
                    print(text)
            else:
                print(text)
        return None

    @magic_arguments()
    @argument("--view", default="general", metavar="VIEW",
              help="general|interconnection|action|package|tree")
    @argument("names", nargs="+", help="element name(s) to visualize")
    @line_magic
    def sysml_viz(self, line: str):
        """%sysml_viz NAME [--view VIEW] — PlantUML view of a named element."""
        args = parse_argstring(self.sysml_viz, line)
        if self.model is None:
            print("sysml: no model loaded — run a %%sysml cell first")
            return None

        from sysmlpy import plantuml as pl

        views = {
            "general": pl.as_general_view,
            "interconnection": pl.as_interconnection_view,
            "action": pl.as_action_flow_view,
            "package": pl.as_package_view,
            "tree": pl.as_tree_diagram,
        }
        view = args.view.lower()
        func = views.get(view)
        if func is None:
            print(f"sysml: unknown view {args.view!r}; "
                  f"one of {', '.join(views)}")
            return None
        for name in args.names:
            results = self.model.find(name)
            if not results:
                print(f"sysml: no elements named {name!r}")
                continue
            for r in results:
                try:
                    print(func(r, style="bw"))
                except Exception as e:
                    print(f"sysml: could not render {name!r}: {e}")
        return None


def load_ipython_extension(ipython):
    magics = SysMLMagics(ipython)
    ipython.register_magics(magics)
    ipython.user_ns.setdefault("_sysml_magics", magics)