#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stereotype-palette selection (accessibility: Okabe-Ito option)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest

import sysmlpy
from sysmlpy import plantuml as pu


MODEL = """
package Vehicles {
    part def Vehicle {
        part engine : Engine;
        attribute mass : ScalarValues::Real;
    }
    part def Engine;
}
"""


@pytest.fixture(autouse=True)
def _restore_palette():
    yield
    pu.set_stereotype_palette("default")


def test_default_palette_unchanged():
    pu.set_stereotype_palette("default")
    text = pu.as_package_view(sysmlpy.loads(MODEL), style="color")
    assert "#32CD32" in text  # the historical lime for parts


def test_okabe_ito_replaces_lime_green():
    pu.set_stereotype_palette("okabe-ito")
    text = pu.as_package_view(sysmlpy.loads(MODEL), style="color")
    assert "#009E73" in text
    assert "#32CD32" not in text


def test_bw_style_renders_no_colors_regardless():
    for palette in ("default", "okabe-ito"):
        pu.set_stereotype_palette(palette)
        text = pu.as_package_view(sysmlpy.loads(MODEL), style="bw")
        assert "#32CD32" not in text
        assert "#009E73" not in text


def test_unknown_palette_raises():
    with pytest.raises(ValueError, match="unknown palette"):
        pu.set_stereotype_palette("neon")


def test_lazy_export():
    assert sysmlpy.set_stereotype_palette is pu.set_stereotype_palette


def test_cooccurring_kinds_stay_distinguishable():
    """Kinds that share views keep distinct Okabe-Ito hues."""
    pu.set_stereotype_palette("okabe-ito")
    colors = {k: v[1] for k, v in pu._stereotype_colors().items()}
    # iv: parts, connections, flows together
    assert len({colors["part"], colors["connection"], colors["flow"]}) == 3
    # afv: actions and flows together
    assert colors["action"] != colors["flow"]
