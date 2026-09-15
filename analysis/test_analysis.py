#!/usr/bin/env python3
"""Small dependency-free checks for the generated analytical contract."""

import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
dashboard = json.loads((ROOT / "client/src/dashboard-data.json").read_text())
qa = json.loads((ROOT / "analysis/qa-report.json").read_text())
controls = dashboard["controls"]

assert qa["pass"]
assert qa["counts"] == {
    "sourceRows": 243,
    "canonicalRows": 243,
    "directRows": 51,
    "shockRows": 192,
    "deliveredRows": 138,
    "heldRows": 54,
    "actionCells": 44,
}
assert math.isclose(controls["postDIFOT"], 113 / 138 * 100)
assert len(dashboard["heldQueue"]) == controls["heldRows"]
assert all(cell["difot"] is None for cell in dashboard["cells"] if cell["kind"] == "held")
assert all(route["adverse"] is None for route in dashboard["routes"] if route["kind"] == "reference")
assert all(item["vectors"] == 50 for item in dashboard["scoreRobustness"].values())
assert len(dashboard["frontier"]) == 6
assert len({scenario["outputs"]["totalContribution"] for scenario in dashboard["scenarios"]}) == 3
print("analytical contract: pass")
