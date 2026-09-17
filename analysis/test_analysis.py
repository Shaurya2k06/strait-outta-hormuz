#!/usr/bin/env python3
"""Invariant and golden-value tests for the generated analytical contract."""

import json
import math
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis"))

from analyze import (  # noqa: E402
    build_route_evidence,
    classify,
    classify_records,
    aggregate,
    parse_workbook,
    run_qa,
    service_interval,
    validate_source,
)


def close(actual, expected, tolerance=0.01):
    assert math.isclose(actual, expected, abs_tol=tolerance), (actual, expected)


def fixture(universe="post_blockade_delivered", route="Cape of Good Hope", difot="Y", cost=12.0, revenue=20.0, tonnes=2.0):
    return {
        "Shipment_ID": f"fixture-{route}-{difot}-{cost}",
        "Route_Type": route,
        "Product_Category": "Test Product",
        "Customer_Name": "Test Customer",
        "Cargo_Type": "Container (TEU)",
        "universe": universe,
        "Cargo_Weight_Tons": tonnes,
        "Cargo_Value_USD": 100.0,
        "Contracted_Freight_Revenue_USD": revenue,
        "Revenue_Recognized_USD": revenue if universe != "held_open" else 0.0,
        "Total_Cost_to_Serve_USD": cost,
        "Freight_Cost_USD": cost - 3.0,
        "Fuel_Cost_USD": 1.0,
        "Insurance_Cost_USD": 1.0,
        "Penalty_Cost_USD": 1.0,
        "Gross_Margin_USD": (revenue if universe != "held_open" else 0.0) - cost,
        "Planned_Transit_Days": 5.0,
        "Actual_Transit_Days": None if universe == "held_open" else 6.0,
        "Delay_Days": 4.0 if universe == "held_open" else 1.0,
        "DIFOT_Met": difot,
        "Route_Margin_Sensitivity_USD": 4.0,
    }


raw, source_info = parse_workbook(ROOT / "R2-WAR ROOM MASTERPLAN-cleaned.xlsx")
source_validation = validate_source(raw, source_info)
dashboard = json.loads((ROOT / "client/src/dashboard-data.json").read_text())
qa = json.loads((ROOT / "analysis/qa-report.json").read_text())

assert source_validation["pass"]
invalid_source = validate_source([{"Shipment_ID": "only-one"}], {"columns": ["Shipment_ID"]})
assert invalid_source["pass"] is False
assert "rowCount" in invalid_source["failedChecks"]
assert "Route_Type" in invalid_source["missingColumns"]
assert qa["pass"]
assert dashboard["schemaVersion"] == "2.0.0"
assert qa["counts"] == {
    "sourceRows": 243,
    "uniqueShipmentIds": 243,
    "directReferenceRows": 51,
    "postBlockadeDeliveredRows": 138,
    "heldOpenRows": 54,
    "decisionCells": 44,
    "decisionRegisterRows": 44,
}

classified = classify_records(raw)
assert classify({"Route_Type": "Direct (Pre-Blockade)"}) == "direct_reference"
assert classify({"Route_Type": "Held in Gulf"}) == "held_open"
assert classify({"Route_Type": "Cape of Good Hope"}) == "post_blockade_delivered"
assert {key: len(value) for key, value in classified.items()} == {
    "direct_reference": 51,
    "post_blockade_delivered": 138,
    "held_open": 54,
}

small = [fixture(), fixture(difot="N", cost=10.0, revenue=22.0, tonnes=3.0)]
small_summary = aggregate(small)
close(small_summary["tonnes"], 5.0)
close(small_summary["totalCost"], 22.0)
close(small_summary["costPerTon"], 4.4)
close(small_summary["contractedRevenuePerTon"], 8.4)
assert small_summary["difotHits"] == 1
assert small_summary["difotDenominator"] == 2
held_summary = aggregate([fixture(universe="held_open", route="Held in Gulf")])
assert held_summary["difot"] is None
assert held_summary["difotDenominator"] == 0

interval = service_interval(0, 1)
assert 0 <= interval["lower"] <= interval["adjusted"] <= interval["upper"] <= 100

dominance_rows = [
    fixture(route="Route A", cost=4.0, difot="Y"),
    fixture(route="Route B", cost=10.0, difot="N"),
]
dominance = build_route_evidence(dominance_rows)
assert dominance[0]["status"] == "observed_pilot_candidate"
assert dominance[0]["causalClaim"] is False
assert dominance[0]["capacityKnown"] is False
assert dominance[0]["rolloutApproved"] is False

golden = qa["golden"]
close(golden["contractedRevenue"], 113_313_425.66)
close(golden["recognizedRevenue"], 87_389_145.83)
close(golden["heldRevenue"], 25_924_279.83)
close(golden["deliveredCost"], 228_026_014.34)
close(golden["deliveredSignedSensitivity"], 166_017_249.42381522, 0.000001)
close(golden["benchmarkContribution"], 8_313_859.03381522, 0.000001)
close(golden["observedDeliveredContribution"], -157_703_390.39)
close(golden["heldCost"], 34_315_352.10)
close(golden["heldPenalty"], 26_015_708.84)
close(golden["heldInsurance"], 4_481_012.26)
close(golden["heldFullLifeGap"], 8_391_072.27)
close(dashboard["portfolio"]["positiveSensitivity"], 178_709_588.63413125, 0.000001)
close(golden["directDIFOT"], 100.0)
close(golden["postBlockadeDIFOT"], 113 / 138 * 100, 0.000001)
close(golden["topThreeCustomerExposureShare"], 90.40679109486456, 0.000001)
close(golden["topTwoProductExposureShare"], 99.10015145853649, 0.000001)

assert dashboard["heldLedger"]["summary"]["shipments"] == 54
assert dashboard["heldLedger"]["summary"]["forwardContribution"] is None
assert all(row["forwardContribution"] is None for row in dashboard["heldLedger"]["rows"])
assert all(cell["difot"] is None for cell in dashboard["decisionCells"] if cell["universe"] == "held_open")
assert all(route["rolloutApproved"] is False for route in dashboard["routeEvidence"])
assert dashboard["appendixDiagnostics"]["compositeScore"]["decisionUse"] is False
assert all("composite" not in cell for cell in dashboard["decisionCells"])
assert all(item["cellId"] in {cell["id"] for cell in dashboard["decisionCells"]} for item in dashboard["decisionRegister"])
assert all(
    not item["posture"]
    or not set(item["posture"]).intersection({"renegotiate_price_or_terms", "route_pilot", "held_triage"})
    or item["approvalGates"]
    for item in dashboard["decisionRegister"]
)

for forbidden in (
    "scenarios",
    "scenarioInputs",
    "scenarioContribution",
    "scenarioDIFOT",
    "unservedTonnes",
    "optionUtilization",
    "costMultiplier",
    "insuranceMultiplier",
    "penaltyMultiplier",
    "clearRate",
    "heldInflowMultiplier",
    "recoveryRate",
    "serviceMultiplier",
    "unavailableRoutes",
):
    assert forbidden not in json.dumps(dashboard)

print("analytical contract: pass")
