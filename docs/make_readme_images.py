"""The README's picture, from the tests' made-up picks (never real data): python docs/make_readme_images.py"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tests"))

from test_analysis import made_up  # noqa: E402

from dataclass_coverage import analyze  # noqa: E402
from dataclass_coverage.matplotlib_view import figure  # noqa: E402

coverage = analyze(made_up(), ranges={"draws": (0, 9), "tcp[0]": (-0.4, 0.4), "tcp[1]": (0.0, 0.6), "tcp[2]": (-0.2, 0.2)},
                   fields=["item", "split", "angle_rad", "grip.width_mm", "grip.force_n", "tcp[0]", "tcp[1]", "speed"],
                   group_by="item", split="split", title="Made-up picks")
fig = figure(coverage.payload, "numbers")
fig.savefig(HERE / "img" / "numbers.png", dpi=80)
print(HERE / "img" / "numbers.png")
