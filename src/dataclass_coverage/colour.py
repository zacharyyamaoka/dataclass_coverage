"""The colour + scale rule every viewer here shares: BAM Reach's five colour maps (17 stops each), Reverse, and the five
count scales (linear clipped at p98, log, equalized, visited, enough). numpy only.

WHY a copy of traj_compare's rule (coverage/matplotlib_view.py, itself a mirror of its page's coverage_color.js), not an
import: this package is public and standalone; tests/test_colour.py pins the stops to data-ui's colormap.js (the stock
coverage views this package's page draws with), so the PNGs, the page and Viser paint the same count the same colour.
WHY linear first (Zach 2026-11-23): "Linear to me is BY far the most informative here". WHY empty is white, never a map
colour (Zach 2026-11-19): "so its clear that white means empty".
"""

from __future__ import annotations

import math
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

# WHY BAM Reach's five maps and "Reverse (high = dark)": Zach, 2026-11-23, "lets just do what we did with like bam
# reach. we can use viridis. but lets make it easy for the user to change ... to other good cmap and switch from high
# to low". The 17 stops are coverage_color.js's (= robot_reach codes.py COLORMAPS); a test pins them equal.
COLORMAPS: dict[str, tuple[tuple[int, int, int], ...]] = {
    "viridis": ((68, 1, 84), (72, 24, 106), (71, 45, 123), (66, 64, 134), (59, 82, 139), (51, 99, 141),
                (44, 114, 142), (38, 130, 142), (33, 145, 140), (31, 160, 136), (40, 174, 128), (63, 188, 115),
                (94, 201, 98), (132, 212, 75), (173, 220, 48), (216, 226, 25), (253, 231, 37)),
    "magma": ((0, 0, 4), (10, 8, 34), (29, 17, 71), (54, 16, 107), (81, 18, 124), (106, 28, 129), (131, 38, 129),
              (156, 46, 127), (183, 55, 121), (208, 65, 111), (231, 82, 99), (245, 107, 92), (252, 137, 97),
              (254, 167, 114), (254, 196, 136), (253, 226, 163), (252, 253, 191)),
    "plasma": ((13, 8, 135), (49, 5, 151), (76, 2, 161), (102, 0, 167), (126, 3, 168), (149, 17, 161),
               (170, 35, 149), (188, 53, 135), (204, 71, 120), (218, 90, 106), (230, 108, 92), (240, 128, 78),
               (248, 149, 64), (253, 172, 51), (253, 197, 39), (248, 223, 37), (240, 249, 33)),
    "inferno": ((0, 0, 4), (11, 7, 36), (33, 12, 74), (61, 9, 101), (87, 16, 110), (113, 25, 110), (138, 34, 106),
                (163, 44, 97), (188, 55, 84), (210, 70, 68), (228, 90, 49), (241, 115, 29), (249, 142, 9),
                (252, 172, 17), (249, 203, 53), (242, 234, 105), (252, 255, 164)),
    "cividis": ((0, 34, 78), (0, 46, 106), (26, 56, 111), (50, 67, 109), (67, 78, 108), (83, 90, 109),
                (97, 101, 111), (111, 112, 115), (125, 124, 120), (140, 136, 120), (155, 148, 118), (171, 160, 114),
                (188, 174, 108), (205, 187, 99), (222, 201, 88), (240, 216, 70), (254, 232, 56)),
}


COLORMAP_NAMES: tuple[str, ...] = tuple(COLORMAPS)


# WHY linear first: Zach 2026-11-23, "Linear to me is BY far the most informative here".
SCALES: tuple[str, ...] = ("linear", "log", "equalized", "visited", "enough")


SCALE_TITLES = {"linear": "linear (clipped at p98)", "log": "log", "equalized": "histogram-equalized",
                "visited": "visited / not", "enough": "≥ enough samples / not"}


# WHY empty is white, never a colormap colour: Zach 2026-11-19, "so its clear that white means empty".
EMPTY_RGB = (255, 255, 255)


OUTSIDE_RGB = (221, 220, 214)  # beyond the limit: the robot cannot go there


LIMIT_COLOR = "#b4442f"  # limit lines: solid = the limit, dashed = the planner's


INK = "#1d1d1f"


MUTED = "#6e6e73"


HAIR = "#d2d2d7"


BARS = "#3d5a80"  # 1-D histograms: one calm ink, so colour stays reserved for "how much" in the heatmaps


# Group colours (Paul Tol "bright", colour-blind safe), in the order of payload["source"]["groups"].
GROUP_COLORS = ("#4477aa", "#ee6677", "#228833", "#ccbb44", "#66ccee", "#aa3377", "#bbbbbb")


def check_colour_choice(cmap: str, scale: str) -> None:
    if cmap not in COLORMAPS:
        raise ValueError(f"cmap={cmap!r}: expected one of {', '.join(COLORMAP_NAMES)}")
    if scale not in SCALES:
        raise ValueError(f"scale={scale!r}: expected one of {', '.join(SCALES)}")


def ramp_rgb(t: Any, cmap: str = "viridis", reverse: bool = False) -> np.ndarray:
    """t in [0, 1] (any shape) -> uint8 RGB (shape + (3,)), interpolating the 17 stops exactly as the page does."""
    stops = np.asarray(COLORMAPS.get(cmap, COLORMAPS["viridis"]), float)
    if reverse:
        stops = stops[::-1]
    last = len(stops) - 1
    x = np.clip(np.asarray(t, float), 0.0, 1.0) * last
    lower = np.minimum(last - 1, np.floor(x)).astype(int)
    fraction = (x - lower)[..., None]
    rgb = stops[lower] + (stops[lower + 1] - stops[lower]) * fraction
    return np.floor(rgb + 0.5).astype(np.uint8)  # Math.round


def tick_label(value: float) -> str:
    """coverage_color.js round(): 412 -> "412", 12.5 -> "12.5", 0.25 -> "0.25", 3 -> "3"."""
    if value >= 100:
        return str(int(math.floor(value + 0.5)))
    if value >= 10:
        text = f"{value:.1f}"
        return text[:-2] if text.endswith(".0") else text
    text = format(value, "#.2g")
    return re.sub(r"\.?0+$", "", text) if "." in text else text


@dataclass(frozen=True)
class Scaled:
    """What a scale did to a count array: `t` (-1 = empty, else 0..1), colour-bar `ticks` [(t, label)], a `note`."""

    t: np.ndarray
    ticks: tuple[tuple[float, str], ...]
    note: str
    top: float
    mode: str


def scale_counts(counts: Any, mode: str = "linear", *, enough: int = 10, clip: float = 0.98,
                 top: float | None = None) -> Scaled:
    """coverage_color.js scale(): counts (None / NaN = no value) -> colour positions, ticks and a note.

    `top` forces the top of the linear / log scale (a shared max across small multiples)."""
    values = np.asarray([np.nan if value is None else value for value in np.ravel(counts)], float).reshape(
        np.shape(counts))
    t = np.full(values.shape, -1.0)
    visited = np.isfinite(values) & (values > 0)
    nonzero = np.sort(values[visited])
    if not len(nonzero):
        return Scaled(t, (), "nothing visited", 0.0, mode)
    highest = float(nonzero[-1])
    if mode == "visited":
        t[visited] = 1.0
        return Scaled(t, ((1.0, "visited"),), f"{len(nonzero)} cells visited", highest, mode)
    if mode == "enough":
        full = visited & (values >= enough)
        t[visited] = 0.25
        t[full] = 1.0
        return Scaled(t, ((0.25, f"< {enough}"), (1.0, f"≥ {enough}")),
                      f"{int(full.sum())} of {len(nonzero)} visited cells have ≥ {enough}", highest, mode)
    if mode == "equalized":
        # WHY it lifts thin cells: each cell's colour is its RANK among visited cells (the empirical CDF), so a cell
        # walked once spreads over the same colour range as one walked 1000 times. It shows WHERE, not HOW MUCH.
        below = np.searchsorted(nonzero, values[visited], side="left")
        upto = np.searchsorted(nonzero, values[visited], side="right")
        t[visited] = ((below + upto - 1) / 2) / (len(nonzero) - 1) if len(nonzero) > 1 else 1.0
        ticks = tuple((q, tick_label(float(np.quantile(nonzero, q)))) for q in (0.0, 0.25, 0.5, 0.75, 1.0))
        return Scaled(t, ticks, "colour = rank among visited cells", highest, mode)
    if mode == "log":
        scale_top = top or highest
        denominator = math.log1p(scale_top)
        t[visited] = np.minimum(1.0, np.log1p(values[visited]) / denominator)
        ticks = [(math.log1p(v) / denominator, tick_label(v)) for v in (1, 10, 100, 1000, 10000, 100000)
                 if v <= scale_top]
        ticks.append((1.0, tick_label(scale_top)))
        return Scaled(t, tuple(ticks), f"log, top {tick_label(scale_top)}", scale_top, mode)
    if mode != "linear":
        raise ValueError(f"scale={mode!r}: expected one of {', '.join(SCALES)}")
    scale_top = top or max(float(np.quantile(nonzero, clip)), float(nonzero[0]))
    t[visited] = np.minimum(1.0, values[visited] / scale_top)
    ticks = tuple((q, tick_label(q * scale_top)) for q in (0.0, 0.25, 0.5, 0.75, 1.0))
    note = (f"clipped at p{round(clip * 100)}: {tick_label(scale_top)} (top cell {tick_label(highest)})"
            if highest > scale_top else f"top {tick_label(scale_top)}")
    return Scaled(t, ticks, note, scale_top, mode)


def edges(block: Sequence[float]) -> np.ndarray:
    """A payload edge triple [low, high, bins] -> the bins + 1 linear edges."""
    low, high, bins = block
    return np.linspace(float(low), float(high), int(bins) + 1)

