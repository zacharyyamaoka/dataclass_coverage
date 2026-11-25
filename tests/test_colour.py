"""The colour rule is the page's: the five maps' 17 stops equal data-ui's coverage views' (colormap.js), so a PNG, the
page and Viser paint the same count the same colour. Skipped where no data-ui checkout is found (DATA_UI)."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import numpy as np
import pytest

from dataclass_coverage.colour import COLORMAP_NAMES, COLORMAPS, ramp_rgb, scale_counts

COLORMAP_JS = Path(os.environ.get("DATA_UI", str(Path.home() / "data-ui"))) / "packages/views/coverage/src/colormap.js"


@pytest.mark.skipif(not COLORMAP_JS.is_file(), reason="needs a data-ui checkout (DATA_UI)")
def test_the_stops_are_data_uis():
    text = COLORMAP_JS.read_text("utf-8")
    for name in COLORMAP_NAMES:
        found = re.search(rf"^\s*{name}: (\[\[.*?\]\]),?$", text, re.M)
        assert found, name
        assert [tuple(stop) for stop in json.loads(found.group(1))] == list(COLORMAPS[name]), name
    assert re.search(r"NAMES = \[(.*?)\]", text).group(1).replace("'", "").split(", ") == list(COLORMAP_NAMES)


def test_the_ramp_ends_on_its_stops_and_reverse_turns_it_round():
    assert tuple(ramp_rgb(0.0)) == COLORMAPS["viridis"][0] and tuple(ramp_rgb(1.0)) == COLORMAPS["viridis"][-1]
    assert tuple(ramp_rgb(0.0, "magma", reverse=True)) == COLORMAPS["magma"][-1]


def test_empty_is_never_a_colour_and_linear_clips_at_p98():
    counts = np.array([0, 1, 2, 3, 100])
    scaled = scale_counts(counts, "linear")
    assert scaled.t[0] == -1  # empty: the surface, never a map colour
    assert scaled.t[-1] == 1.0 and "clipped at p98" in scaled.note
