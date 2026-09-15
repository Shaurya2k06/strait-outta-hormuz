#!/usr/bin/env python3
"""Small dependency-free checks for the generated analytical contract."""

import json
import math
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis"))
from analyze import (  # noqa: E402
    PROPOSAL_ROUTE_INPUTS,
    SCENARIO_DEFINITIONS,
    canonicalize,
    constrained_forward_ledger,
    parse_workbook,
    scenario_outputs,
    source_gate_status,
)


dashboard = json.loads((ROOT / "client/src/dashboard-data.json").read_text())
qa = json.loads((ROOT / "analysis/qa-report.json").read_text())
controls = dashboard["controls"]

assert qa["pass"]
assert not qa["boardSafe"]
assert qa["sourceGate"]["pass"]
assert qa["counts"] == {
    "sourceRows": 243,
    "rawRows": 243,
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
assert all(
    scenario["decisionReady"] is False
    and scenario["outputs"] == {"locked": True}
    and scenario["diagnostics"] is None
    and scenario["flow"] is None
    for scenario in dashboard["scenarios"]
)

raw, _ = parse_workbook(ROOT / "R2-WAR ROOM MASTERPLAN-cleaned.xlsx")
canonical, duplicate_info = canonicalize(raw)
assert len(raw) == 243 and len(canonical) == 243
assert duplicate_info["duplicateExcessRows"] == 0

duplicate_rows = []
for shipment_id in ("SGL-1004", "SGL-1081", "SGL-1130"):
    row = {"Shipment_ID": shipment_id, "value": 1}
    duplicate_rows.extend([row, dict(row)])
canonical, duplicate_info = canonicalize(duplicate_rows)
assert len(duplicate_rows) == 6 and len(canonical) == 3
assert duplicate_info["duplicateExcessRows"] == 3
assert {item["shipmentId"] for item in duplicate_info["adjudicationTable"]} == {"SGL-1004", "SGL-1081", "SGL-1130"}
assert canonicalize([{"Shipment_ID": ""}])[1]["blankShipmentIdRows"] == [2]
synthetic_gate = source_gate_status(
    {"sourceRows": 6, "sourceSha256": "approved", "sourceFile": "raw.xlsx"},
    duplicate_info,
    3,
    {
        "approvedRawRows": 6,
        "expectedCanonicalRows": 3,
        "expectedDuplicateExcessRows": 3,
        "expectedExactDuplicateShipmentIds": ["SGL-1004", "SGL-1081", "SGL-1130"],
        "approvedSha256": "approved",
        "approvedRawSourceFile": "raw.xlsx",
        "contractVersion": "source-contract-v1",
    },
)
assert synthetic_gate["pass"]

held = [row for row in canonicalize(raw)[0] if row["Route_Type"] == "Held in Gulf"]
base_inputs = dict(SCENARIO_DEFINITIONS[0]["inputs"])
zero_clear = dict(base_inputs, clearRate=0)
full_clear = dict(base_inputs, clearRate=1)
all_routes_closed = dict(base_inputs, unavailableRoutes=list(PROPOSAL_ROUTE_INPUTS))
zero = constrained_forward_ledger(held, zero_clear, PROPOSAL_ROUTE_INPUTS)
full = constrained_forward_ledger(held, full_clear, PROPOSAL_ROUTE_INPUTS)
shutdown = constrained_forward_ledger(held, base_inputs, PROPOSAL_ROUTE_INPUTS)
closed = constrained_forward_ledger(held, all_routes_closed, PROPOSAL_ROUTE_INPUTS)
assert zero["clearedTonnes"] == 0
assert full["endingHeldTonnes"] < zero["endingHeldTonnes"]
assert shutdown["clearedTonnes"] > closed["clearedTonnes"]
assert shutdown["forwardContribution"] != closed["forwardContribution"]
assert closed["clearedTonnes"] == 0

approved_scenarios = scenario_outputs(
    SCENARIO_DEFINITIONS,
    held,
    {"pass": True},
    {"ready": True},
    {"routes": PROPOSAL_ROUTE_INPUTS},
)
assert all(
    scenario["decisionReady"]
    and scenario["outputs"]["locked"] is False
    and scenario["outputs"]["flowBalanced"]
    and scenario["diagnostics"]["referenceRevenueIncluded"] == 0
    and all(
        allocation["allocatedTonnes"] <= allocation["capacityTonnes"] + 0.01
        for allocation in scenario["outputs"]["routeAllocation"]
    )
    for scenario in approved_scenarios
)
print("analytical contract: pass")
