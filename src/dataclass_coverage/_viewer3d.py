"""The 3-D viewer the Viser view draws on: the house ``viser_3d_viewer`` when it is installed, else plain ``viser`` with
the same rules (loopback only, no viser logo, port 0 = the OS picks, a ``READY <url>`` line, a camera that frames the
box). Plus the small scene and legend helpers the view shares with traj_compare's coverage viewers.

WHY optional: viser_3d_viewer (ViewCube, Fusion-style camera) is not published, and this package is; a public install
gets the plain viewer, a machine with the house viewer gets the house one. Both expose what the view uses:
``.server``, ``.config.host`` / ``.show_logo``, ``.port``, ``.url``, ``.camera.fit_home`` / ``.fit`` / ``.add_gui``,
``.add_status``, ``.print_ready()``, ``.serve_forever()``, ``.stop()``.
"""

from __future__ import annotations

import math
import signal
import threading
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np


def open_viewer(*, title: str, port: int = 0) -> Any:
    """A started viewer: the house one when importable, else ``PlainViewer``."""
    try:
        from viser_3d_viewer import Viewer, ViewerConfig
    except ImportError:
        return PlainViewer(title=title, port=port)
    # WHY light, no grid: the PNGs and the page are light (white = empty), and the declared box is the frame here; a
    # floor grid at z = 0 would cut through a box that spans it.
    return Viewer(ViewerConfig(title=title, port=port, dark_mode=False, grid=False))


@dataclass(frozen=True)
class PlainConfig:
    title: str
    port: int = 0
    host: str = "127.0.0.1"  # WHY loopback: viser's own default (0.0.0.0) shows the viewer to the whole LAN
    show_logo: bool = False
    dark_mode: bool = False


class PlainStatus:
    """A markdown table of label / value rows in the panel (the house viewer's Status, minimal)."""

    def __init__(self, server: Any, label: str) -> None:
        self._label, self._rows = label, {}
        self._markdown = server.gui.add_markdown(self._render())

    def _render(self) -> str:
        rows = "".join(f"| {key} | {value} |\n" for key, value in self._rows.items())
        return f"**{self._label}**\n\n| | |\n|---|---|\n{rows}" if rows else f"**{self._label}**"

    def set(self, **rows: Any) -> None:
        for key, value in rows.items():
            if value is None:
                self._rows.pop(key, None)
            else:
                self._rows[key] = value
        self._markdown.content = self._render()


class PlainCamera:
    """Frame a box: ``fit_home`` sets where every new client starts, ``fit`` moves the connected ones now."""

    FOV = math.radians(50.0)

    def __init__(self, server: Any) -> None:
        self.server = server
        self.home: tuple[np.ndarray, np.ndarray] | None = None
        server.on_client_connect(self._place)

    def _pose(self, low: Sequence[float], high: Sequence[float], direction: Sequence[float] | None,
              margin: float) -> tuple[np.ndarray, np.ndarray]:
        low, high = np.asarray(low, float), np.asarray(high, float)
        centre = (low + high) / 2.0
        radius = max(float(np.linalg.norm(high - low)) / 2.0, 1e-6)
        way = np.asarray(direction if direction is not None else (1.0, -1.3, 0.9), float)
        way = way / np.linalg.norm(way)
        return centre + way * radius * margin / math.tan(self.FOV / 2.0), centre

    def fit_home(self, low, high, direction=None, margin: float = 1.15, aspect: float = 1.0) -> None:
        self.home = self._pose(low, high, direction, margin)

    def fit(self, low, high, direction=None, client=None, margin: float = 1.15) -> None:
        pose = self._pose(low, high, direction, margin)
        for handle in ([client] if client is not None else self.server.get_clients().values()):
            self._set(handle, pose)

    def _place(self, client: Any) -> None:
        if self.home is not None:
            self._set(client, self.home)

    @staticmethod
    def _set(client: Any, pose: tuple[np.ndarray, np.ndarray]) -> None:
        position, look_at = pose
        client.camera.up_direction = (0.0, 0.0, 1.0)
        client.camera.position = tuple(float(v) for v in position)
        client.camera.look_at = tuple(float(v) for v in look_at)

    def add_gui(self, folder: str = "Camera", bounds: Callable[[], tuple] | None = None, expanded: bool = False) -> None:
        with self.server.gui.add_folder(folder, expand_by_default=expanded):
            button = self.server.gui.add_button("Home")

            @button.on_click
            def _(event: Any) -> None:
                if self.home is not None and event.client is not None:
                    self._set(event.client, self.home)


class PlainViewer:
    """Plain viser, configured the house way (see the module docstring)."""

    def __init__(self, *, title: str, port: int = 0) -> None:
        import viser

        self.config = PlainConfig(title=title, port=port)
        self.server = viser.ViserServer(host=self.config.host, port=port, label=title)
        self.server.gui.configure_theme(show_logo=False, dark_mode=False)
        self.server.scene.set_up_direction("+z")
        self.port = int(self.server.get_port())
        if port and self.port != port:  # WHY: viser falls back to another port when one is taken; say so, never guess
            self.server.stop()
            raise OSError(f"port {port} is taken (viser offered {self.port})")
        self.camera = PlainCamera(self.server)
        self._stopped = threading.Event()

    @property
    def url(self) -> str:
        return f"http://{self.config.host}:{self.port}/"

    def add_status(self, label: str = "Status", order: float | None = None) -> PlainStatus:
        return PlainStatus(self.server, label)

    def print_ready(self) -> None:
        print(f"READY {self.url}", flush=True)

    def serve_forever(self) -> None:
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, lambda *_: self._stopped.set())
        self._stopped.wait()
        self.stop()

    def stop(self) -> None:
        self._stopped.set()
        self.server.stop()


# ── the scene and legend helpers (traj_compare coverage/viser_view.py's) ────────────────────────────────────────────


def _box_segments(low: np.ndarray, high: np.ndarray) -> np.ndarray:
    corners = np.array([[x, y, z] for x in (low[0], high[0]) for y in (low[1], high[1]) for z in (low[2], high[2])])
    pairs = [(a, b) for a in range(8) for b in range(a + 1, 8) if bin(a ^ b).count("1") == 1]
    return corners[np.array(pairs)]


def _swatch(css: str, border: bool = False) -> str:
    edge = "border:1px solid #c8c8ce;" if border else ""
    return (f'<span style="display:inline-block;width:10px;height:10px;margin-right:6px;vertical-align:-1px;'
            f'background:{css};{edge}"></span>')


def _bar(css: str) -> str:
    return (f'<span style="display:inline-block;width:14px;height:0;border-top:2px {css};margin-right:6px;'
            f'vertical-align:3px"></span>')
