"""Writing the page's files: atomic writes, the .base YAML writer, the series slots, and vendoring data-ui (copied from
traj_compare's _files.py and coverage/workbench.py, so this package stands alone).

data-ui (https://github.com/zacharyyamaoka/data-ui, public) is vendored into a page's folder by its own ``vendor``
command from a checkout: ``DATA_UI`` names it (default ``~/data-ui``). ``kit=`` reuses one already vendored instead.
"""

from __future__ import annotations

import itertools
import json
import os
import re
import subprocess
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path

DATA_UI = Path(os.environ.get("DATA_UI", str(Path.home() / "data-ui")))

_COUNT = itertools.count()  # WHY a counter beside the pid: two writers in one process (serve's threads) never share a name


def temporary_name(path: Path) -> Path:
    """The temporary name ``path`` is written under: hidden, beside it (one filesystem, so the rename is atomic)."""
    return path.with_name(f".{path.name}.{os.getpid()}-{next(_COUNT)}.tmp")


@contextmanager
def replacing(path: Path | str) -> Iterator[Path]:
    """Yield the temporary name to write ``path``'s new content to; on success it replaces ``path``, else it is deleted.

    For writers that want a path of their own (rerun, ffmpeg, pyarrow): ``with replacing(out) as temporary: ...``.
    """
    path = Path(path)
    temporary = temporary_name(path)
    try:
        yield temporary
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def write_text(path: Path | str, text: str) -> Path:
    """``Path.write_text`` (UTF-8) through a temporary name."""
    with replacing(path) as temporary:
        temporary.write_text(text, encoding="utf-8")
    return Path(path)



# WHY these slots: data-ui's series 4 is amber, 6 green and 8 red, which read as a status (CONTRACT §32); a dataset is
# a family, never a verdict (the round's P1/P5 measured 1, 2, 3, 7 on the four UR5e datasets)
SLOTS = (1, 2, 3, 7, 5)


SPLIT_SLOTS = (5, 4, 6)  # pink, amber, dark green: data-ui series slots the datasets reach last; never 8 (red)



def _write_json(path: Path, document: dict) -> None:
    # WHY allow_nan=False: a NaN would make JSON.parse throw in the browser; every number here is finite or None
    write_text(path, json.dumps(document, separators=(",", ":"), allow_nan=False, ensure_ascii=False) + "\n")


def _vendor(out: Path, ref: str, data_ui: Path) -> str:
    """data-ui ``ref`` into out/vendor/data-ui with data-ui's own vendor command (a clean archive, sha-checked)."""
    cli = data_ui / "bin" / "data-ui.mjs"
    if not cli.is_file():
        raise FileNotFoundError(f"no data-ui checkout at {data_ui} to vendor from; pass kit= (an href to a vendored kit) "
                                "or data_ui= (the checkout)")
    target = out / "vendor" / "data-ui"
    result = subprocess.run(["node", str(cli), "vendor", ref, "--into", str(target)], capture_output=True, text=True,
                            timeout=600)
    if result.returncode != 0:
        raise RuntimeError(f"data-ui vendor {ref} failed: {(result.stderr or result.stdout)[-2000:]}")
    return "vendor/data-ui"



_PLAIN = re.compile(r"^[A-Za-z_][A-Za-z0-9_ .·×/-]*$")


_RESERVED = {"true", "false", "null", "yes", "no", "on", "off", "y", "n", "~"}


def _scalar(value) -> str:
    if value is None:
        return "null"
    if value is True or value is False:
        return "true" if value else "false"
    if isinstance(value, int | float):
        return json.dumps(value)
    text = str(value)
    if _PLAIN.match(text) and text.lower() not in _RESERVED and not text.endswith(" ") and ": " not in text:
        return text
    return "'" + text.replace("'", "''") + "'"


def _flow(value) -> str:
    if isinstance(value, Mapping):
        return "{ " + ", ".join(f"{_scalar(k)}: {_flow(v)}" for k, v in value.items()) + " }" if value else "{}"
    if isinstance(value, list | tuple):
        return "[" + ", ".join(_flow(v) for v in value) + "]"
    return _scalar(value)


def _simple(value) -> bool:
    """Short enough and flat enough for one flow line."""
    return len(_flow(value)) <= 110 and not any(isinstance(v, Mapping) and any(isinstance(w, Mapping | list) for w in v.values())
                                                 for v in (value.values() if isinstance(value, Mapping) else value))


def _yaml(value, indent: int = 0) -> str:
    pad = " " * indent
    lines = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            if isinstance(item, Mapping | list | tuple) and item and not _simple(item):
                lines.append(f"{pad}{_scalar(key)}:")
                lines.append(_yaml(item, indent + 2))
            else:
                lines.append(f"{pad}{_scalar(key)}: {_flow(item)}")
    else:
        for item in value:
            if isinstance(item, Mapping) and item and not _simple(item):
                block = _yaml(item, indent + 2)
                lines.append(f"{pad}- {block.lstrip()}")
            else:
                lines.append(f"{pad}- {_flow(item)}")
    return "\n".join(lines)

