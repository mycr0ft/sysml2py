"""End-to-end tests for the %%sysml IPython magic (requires sysmlpy[jupyter])."""
from __future__ import annotations

import pytest

pytest.importorskip("IPython")

from IPython.core.interactiveshell import InteractiveShell
from IPython.testing.globalipapp import get_ipython  # noqa: E402

import sysmlpy.ipython_magic as im  # noqa: E402


@pytest.fixture
def ip():
    """A fresh IPython shell with the magic loaded and isolated namespaces."""
    InteractiveShell.clear_instance()
    shell = InteractiveShell.instance()
    shell.run_cell("%load_ext sysmlpy.ipython_magic")
    yield shell
    shell.run_cell("%sysml_reset")
    InteractiveShell.clear_instance()


CELL = """%%sysml
package Vehicle {
    part def Engine {
        attribute fuelRate : Real;
    }
    part def Vehicle {
        part engine : Vehicle::Engine;
    }
}"""


def test_load_ext_binds_magics(ip):
    assert "sysml" in ip.magics_manager.magics["cell"]
    assert "sysml_reset" in ip.magics_manager.magics["line"]
    assert "sysml_list" in ip.magics_manager.magics["line"]
    assert "sysml_show" in ip.magics_manager.magics["line"]
    assert "sysml_viz" in ip.magics_manager.magics["line"]


def test_parse_and_namespace_exposure(ip):
    r = ip.run_cell(CELL)
    assert not r.error_in_exec, r.error_in_exec
    names = [p.name for p in ip.user_ns["model"].packages]
    assert names == ["Vehicle"]
    # both aliases point at the same session model
    assert ip.user_ns["_sysml"] is ip.user_ns["model"]


def test_member_granular_merge(ip):
    ip.run_cell(CELL)
    r = ip.run_cell("%%sysml\npackage Vehicle {\n    part def Vehicle;\n}")
    assert not r.error_in_exec, r.error_in_exec
    # Engine (sibling member) survives the Vehicle part redefinition
    assert ip.user_ns["model"].find(name="Engine")
    # exactly one Vehicle part def (sysml_type is 'part'; definitions have
    # definition=True)
    assert [v.name for v in ip.user_ns["model"].find(
        name="Vehicle", sysml_type="part")] == ["Vehicle"]


def test_parse_error_resilient(ip):
    ip.run_cell(CELL)
    r = ip.run_cell("%%sysml\npackage Broken {\n    part def ???\n}")
    assert not r.error_in_exec  # reported to stderr, session survives
    assert ip.user_ns["model"].find(name="Engine")  # prior model intact


def test_sysml_list(ip, capsys):
    ip.run_cell(CELL)
    ip.run_line_magic("sysml_list", "")
    assert "Vehicle" in capsys.readouterr().out
    ip.run_line_magic("sysml_list", "Engine")
    assert "Engine" in capsys.readouterr().out


def test_sysml_show(ip, capsys):
    ip.run_cell(CELL)
    ip.run_line_magic("sysml_show", "Engine")
    out = capsys.readouterr().out
    assert "fuelRate" in out
    ip.run_line_magic("sysml_show", "Engine --json")
    assert "{" in capsys.readouterr().out


def test_sysml_viz(ip, capsys):
    ip.run_cell(CELL)
    ip.run_line_magic("sysml_viz", "Vehicle --view tree")
    out = capsys.readouterr().out
    assert "@startuml" in out
    assert "Engine" in out
    # unknown view degrades gracefully
    ip.run_line_magic("sysml_viz", "Vehicle --view bogus")
    assert "unknown view" in capsys.readouterr().out


def test_sysml_reset(ip):
    ip.run_cell(CELL)
    ip.run_line_magic("sysml_reset", "")
    assert "model" not in ip.user_ns
    ip.run_cell("%%sysml\npackage Fresh {\n    part def Only;\n}")
    assert [p.name for p in ip.user_ns["model"].packages] == ["Fresh"]


def test_file_option(ip, tmp_path):
    f = tmp_path / "m.sysml"
    f.write_text("package FromFile {\n    part def RemotePart;\n}\n")
    r = ip.run_cell(f"%%sysml --file {f}\n-")
    assert not r.error_in_exec, r.error_in_exec
    assert "FromFile" in [p.name for p in ip.user_ns["model"].packages]


def test_viz_views_registry(ip):
    from sysmlpy.plantuml import (
        as_action_flow_view,
        as_general_view,
        as_interconnection_view,
        as_package_view,
        as_tree_diagram,
    )
    assert as_general_view and as_tree_diagram  # registry wiring smoke