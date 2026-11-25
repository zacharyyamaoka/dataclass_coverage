"""Matplotlib drawing helpers (copied from traj_compare's coverage/matplotlib_view.py with the colour rule, so a figure
here looks like a trajectory-coverage figure). matplotlib is imported only inside the functions, through its object API.
"""

from __future__ import annotations

import textwrap
from collections.abc import Sequence

import numpy as np

from .colour import COLORMAPS, HAIR, INK, LIMIT_COLOR, MUTED, OUTSIDE_RGB, SCALE_TITLES, Scaled, ramp_rgb

STYLE = {
    "font.family": "DejaVu Sans", "font.size": 9.0, "axes.titlesize": 9.5, "axes.titlelocation": "left",
    "axes.edgecolor": HAIR, "axes.labelcolor": INK, "axes.titlecolor": INK, "axes.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False, "xtick.color": MUTED, "ytick.color": MUTED,
    "xtick.labelsize": 8.0, "ytick.labelsize": 8.0, "legend.frameon": False, "legend.fontsize": 8.5,
    "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white",
    "figure.constrained_layout.h_pad": 0.06, "figure.constrained_layout.w_pad": 0.06,
}


def _colormap(cmap: str, reverse: bool):
    from matplotlib.colors import LinearSegmentedColormap

    stops = np.asarray(COLORMAPS[cmap], float) / 255.0
    if reverse:
        stops = stops[::-1]
    colormap = LinearSegmentedColormap.from_list(f"{cmap}{'_r' if reverse else ''}", stops, N=256)
    return colormap.with_extremes(bad="white")  # masked = empty = the page


def _new_figure(width: float, height: float):
    from matplotlib.figure import Figure

    return Figure(figsize=(width, height), layout="constrained", dpi=130)


def _header(fig, question: str, footnote: str, handles: list, columns: int | None = None) -> None:
    """The question as the title, the legend (every mark the figure draws) right under it, the data line at the foot.

    WHY the question is the legend's title, not a suptitle: constrained layout stacks an "outside" legend under the
    axes area but not under a suptitle, so the two overlapped; as one block they can't."""
    legend = fig.legend(handles=handles, loc="outside upper left", ncols=columns or min(len(handles), 4),
                        handlelength=1.6, columnspacing=1.6, borderaxespad=0.3, title=question, alignment="left",
                        title_fontproperties={"weight": "bold", "size": 12.5})
    legend.get_title().set_color(INK)
    # ~16 characters an inch at 8 pt: wrapped so a long data line never runs off the PNG's right edge
    fig.supxlabel(textwrap.fill(footnote, width=int(fig.get_figwidth() * 16)), x=0.01, ha="left", fontsize=8,
                  color=MUTED, linespacing=1.3)


def _patch(color, label: str, edge: str | None = None):
    from matplotlib.patches import Patch

    return Patch(facecolor=color, edgecolor=edge or (HAIR if color in ("white", "#ffffff") else color), label=label)


def _line(label: str, color: str = LIMIT_COLOR, style: str = "-", width: float = 1.4):
    from matplotlib.lines import Line2D

    return Line2D([], [], color=color, linestyle=style, linewidth=width, label=label)


def _rgb_hex(rgb: Sequence[int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*(int(c) for c in rgb))


def _ramp_patch(cmap: str, reverse: bool, label: str):
    """A legend swatch that shows the ramp (three stops) so 'colour = how much' reads in the legend too."""
    return _patch(_rgb_hex(ramp_rgb(0.6, cmap, reverse)), label)


def _heat(ax, x_edges: np.ndarray, y_edges: np.ndarray, t: np.ndarray, colormap, outside: np.ndarray | None = None):
    """t[i, j] over x bin i, y bin j (-1 = empty -> white); `outside` cells painted the beyond-the-limit grey."""
    from matplotlib.colors import ListedColormap

    shown = np.ma.masked_where(t < 0, t)
    mesh = ax.pcolormesh(x_edges, y_edges, shown.T, cmap=colormap, vmin=0.0, vmax=1.0, shading="flat",
                         rasterized=True)
    if outside is not None and np.any(outside):
        grey = np.ma.masked_where(~outside.T, np.ones(outside.T.shape))
        ax.pcolormesh(x_edges, y_edges, grey, cmap=ListedColormap([_rgb_hex(OUTSIDE_RGB)]), vmin=0, vmax=1,
                      shading="flat", rasterized=True)
    return mesh


def _colorbar(fig, mesh, axes, scaled: Scaled, label: str, **options):
    bar = fig.colorbar(mesh, ax=axes, fraction=0.05, pad=0.02, aspect=28, **options)
    bar.outline.set_visible(False)
    if scaled.ticks:
        bar.set_ticks([t for t, _ in scaled.ticks], labels=[text for _, text in scaled.ticks])
    bar.ax.tick_params(labelsize=8, colors=MUTED, length=2)
    bar.set_label(f"{label}\n{SCALE_TITLES[scaled.mode]}", fontsize=8.5, color=INK)
    return bar


def _locator(count: int):
    from matplotlib.ticker import MaxNLocator

    return MaxNLocator(count)

