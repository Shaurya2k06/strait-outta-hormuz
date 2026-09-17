#!/usr/bin/env python3
"""Generate the dataset-only analytical engine output.

The workbook is the only analytical input. This module deliberately keeps
historical evidence, derived ledgers and conditional decision gates separate:
it does not manufacture a forward forecast, route capacity or recovery rate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from zipfile import BadZipFile, ZipFile
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WORKBOOK = ROOT / "R2-WAR ROOM MASTERPLAN-cleaned.xlsx"
DASHBOARD_PATH = ROOT / "client/src/dashboard-data.json"
QA_PATH = ROOT / "analysis/qa-report.json"
SCHEMA_VERSION = "2.0.0"
EXPECTED_SOURCE_ROWS = 243
EPSILON_CENTS = 0.01

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS = {"m": MAIN_NS}

REQUIRED_COLUMNS = [
    "Shipment_ID", "Departure_Date", "Route_Type", "Product_Category", "Cargo_Type",
    "Customer_Name", "Customer_Region", "Customer_Since", "Cargo_Weight_Tons",
    "Cargo_Value_USD", "Contracted_Freight_Revenue_USD", "Planned_Transit_Days",
    "Actual_Transit_Days", "Delay_Days", "Freight_Cost_USD", "Fuel_Cost_USD",
    "Insurance_Cost_USD", "Penalty_Cost_USD", "Total_Cost_to_Serve_USD",
    "Revenue_Recognized_USD", "Gross_Margin_USD", "Gross_Margin_Pct", "DIFOT_Met",
    "Cost_per_Ton_USD", "Revenue_per_Ton_USD", "Route_Margin_Sensitivity_USD",
    "Customer_Concentration_Risk_Pct", "War_Risk_Insurance_Burden_Pct",
    "Delay_Cost_Attribution_Pct",
]
TEXT_FIELDS = {
    "Shipment_ID", "Departure_Date", "Route_Type", "Product_Category", "Cargo_Type",
    "Customer_Name", "Customer_Region", "DIFOT_Met",
}
NUMERIC_FIELDS = [field for field in REQUIRED_COLUMNS if field not in TEXT_FIELDS]

ROUTE_ORDER = [
    "Direct (Pre-Blockade)", "Cape of Good Hope", "Pipeline Bypass", "Overland Truck",
    "Air Bridge", "Held in Gulf",
]

APPROVAL_GATES = {
    "LIVE_ALL_IN_QUOTE": {"name": "LIVE_ALL_IN_QUOTE", "status": "missing", "ownerRole": "Supply Chain Head", "requiredFor": "route_pilot_authorization", "value": None, "effectiveDate": None, "approvedBy": None},
    "ROUTE_WEEK_CAPACITY": {"name": "ROUTE_WEEK_CAPACITY", "status": "missing", "ownerRole": "Network Planning", "requiredFor": "route_pilot_authorization", "value": None, "effectiveDate": None, "approvedBy": None},
    "PRODUCT_CARGO_FEASIBILITY": {"name": "PRODUCT_CARGO_FEASIBILITY", "status": "missing", "ownerRole": "Operations Head", "requiredFor": "route_pilot_authorization", "value": None, "effectiveDate": None, "approvedBy": None},
    "INSURANCE_TERMS": {"name": "INSURANCE_TERMS", "status": "missing", "ownerRole": "Risk/Insurance Lead", "requiredFor": "route_pilot_authorization", "value": None, "effectiveDate": None, "approvedBy": None},
    "SERVICE_REQUIREMENT": {"name": "SERVICE_REQUIREMENT", "status": "missing", "ownerRole": "Operations Head", "requiredFor": "route_pilot_authorization", "value": None, "effectiveDate": None, "approvedBy": None},
    "CUSTOMER_RECOVERY_TERM": {"name": "CUSTOMER_RECOVERY_TERM", "status": "missing", "ownerRole": "Commercial Head", "requiredFor": "commercial_recovery_authorization", "value": None, "effectiveDate": None, "approvedBy": None},
    "EFFECTIVE_DATE": {"name": "EFFECTIVE_DATE", "status": "missing", "ownerRole": "Finance Lead", "requiredFor": "decision_activation", "value": None, "effectiveDate": None, "approvedBy": None},
    "APPROVING_OWNER": {"name": "APPROVING_OWNER", "status": "missing", "ownerRole": "Finance Lead", "requiredFor": "decision_activation", "value": None, "effectiveDate": None, "approvedBy": None},
}
ROUTE_PILOT_GATES = ["LIVE_ALL_IN_QUOTE", "ROUTE_WEEK_CAPACITY", "PRODUCT_CARGO_FEASIBILITY", "INSURANCE_TERMS", "SERVICE_REQUIREMENT", "EFFECTIVE_DATE", "APPROVING_OWNER"]
COMMERCIAL_GATES = ["CUSTOMER_RECOVERY_TERM", "EFFECTIVE_DATE", "APPROVING_OWNER"]
HELD_RELEASE_GATES = [*ROUTE_PILOT_GATES, "CUSTOMER_RECOVERY_TERM"]


def column_number(reference: str) -> int:
    letters = "".join(character for character in reference if character.isalpha())
    value = 0
    for character in letters:
        value = value * 26 + ord(character.upper()) - ord("A") + 1
    return value - 1


def cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    value = cell.find("m:v", NS)
    if value is None:
        inline = cell.find("m:is", NS)
        return "".join(item.text or "" for item in inline.iter(f"{{{MAIN_NS}}}t")) if inline is not None else ""
    raw = value.text or ""
    return shared_strings[int(raw)] if cell.attrib.get("t") == "s" else raw


def parse_workbook(path: Path) -> tuple[list[dict], dict]:
    """Parse the Shipment_Data worksheet and normalize numeric fields."""
    path = Path(path)
    with ZipFile(path) as archive:
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            shared_strings = ["".join(item.text or "" for item in string.iter(f"{{{MAIN_NS}}}t")) for string in root]
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        relation_map = {item.attrib["Id"]: item.attrib["Target"] for item in relationships}
        shipment_sheet = next(sheet for sheet in workbook.findall("m:sheets/m:sheet", NS) if sheet.attrib["name"] == "Shipment_Data")
        relation_id = shipment_sheet.attrib[f"{{{REL_NS}}}id"]
        sheet = ET.fromstring(archive.read(f"xl/{relation_map[relation_id].lstrip('/')}"))
        rows = sheet.findall(".//m:row", NS)
        width = max((column_number(cell.attrib.get("r", "")) for row in rows for cell in row.findall("m:c", NS)), default=0) + 1

        def values(row: ET.Element) -> list[str]:
            result = [""] * width
            for cell in row.findall("m:c", NS):
                result[column_number(cell.attrib.get("r", ""))] = cell_value(cell, shared_strings)
            return result

        header_values = values(rows[0])
        headers = [header for header in header_values if header]
        numeric_fields = set(headers) - TEXT_FIELDS
        parsed: list[dict] = []
        for row_number, row in enumerate(rows[1:], 2):
            values_by_column = values(row)
            if not any(values_by_column[index] for index, header in enumerate(header_values) if header):
                continue
            record = {header: values_by_column[index] for index, header in enumerate(header_values) if header}
            for field in numeric_fields:
                raw = record.get(field, "")
                if raw in (None, ""):
                    record[field] = None
                else:
                    try:
                        record[field] = float(raw)
                    except (TypeError, ValueError) as error:
                        raise ValueError(f"numeric field {field} failed to parse at workbook row {row_number}") from error
            for field in TEXT_FIELDS:
                if field in record and record[field] is not None:
                    record[field] = str(record[field]).strip()
            parsed.append(record)
    source_bytes = path.read_bytes()
    return parsed, {
        "sourceFile": path.name, "sourceSheet": "Shipment_Data", "sourceRows": len(parsed),
        "columns": headers, "sourceSha256": hashlib.sha256(source_bytes).hexdigest(),
        "sourceSizeBytes": len(source_bytes),
    }


def _counts(values: list[str]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for item in values:
        counts[item] += 1
    return counts


def validate_source(records: list[dict], source_info: dict | None = None) -> dict:
    """Validate the accepted 243-row source contract before calculation."""
    source_info = source_info or {}
    present_columns = set(source_info.get("columns", [])) or (set(records[0]) if records else set())
    missing_columns = [field for field in REQUIRED_COLUMNS if field not in present_columns]
    shipment_ids = [str(record.get("Shipment_ID") or "").strip() for record in records]
    nonblank_ids = [shipment_id for shipment_id in shipment_ids if shipment_id]
    duplicate_ids = sorted(shipment_id for shipment_id, count in _counts(nonblank_ids).items() if count > 1)
    numeric_parse_failures = []
    for index, record in enumerate(records, 2):
        for field in NUMERIC_FIELDS:
            field_value = record.get(field)
            if field_value is not None and (not isinstance(field_value, (int, float)) or not math.isfinite(float(field_value))):
                numeric_parse_failures.append(f"row {index}: {field}")
        if record.get("Route_Type") != "Held in Gulf" and record.get("Actual_Transit_Days") is None:
            numeric_parse_failures.append(f"row {index}: Actual_Transit_Days missing for completed shipment")
    checks = {
        "rowCount": len(records) == EXPECTED_SOURCE_ROWS,
        "requiredColumns": not missing_columns,
        "nonblankShipmentIds": len(nonblank_ids) == len(records),
        "uniqueShipmentIds": len(set(nonblank_ids)) == EXPECTED_SOURCE_ROWS,
        "numericFieldsParse": not numeric_parse_failures,
    }
    failed = [name for name, passed in checks.items() if not passed]
    return {
        "pass": not failed, "sourceStatus": "accepted" if not failed else "rejected", "checks": checks,
        "failedChecks": failed, "missingColumns": missing_columns, "duplicateShipmentIds": duplicate_ids,
        "numericParseFailures": numeric_parse_failures, "sourceRows": len(records),
        "uniqueShipmentIds": len(set(nonblank_ids)),
    }


def classify(record: dict) -> str:
    route = record["Route_Type"]
    if route == "Direct (Pre-Blockade)":
        return "direct_reference"
    if route == "Held in Gulf":
        return "held_open"
    return "post_blockade_delivered"


def classify_records(records: list[dict]) -> dict[str, list[dict]]:
    classified = {"direct_reference": [], "post_blockade_delivered": [], "held_open": []}
    for record in records:
        enriched = dict(record)
        enriched["universe"] = classify(record)
        classified[enriched["universe"]].append(enriched)
    return classified


def record_universe(record: dict) -> str:
    return record.get("universe") or classify(record)


def number(record: dict, field: str) -> float:
    raw = record.get(field)
    return float(raw) if isinstance(raw, (int, float)) and math.isfinite(float(raw)) else 0.0


def ratio(numerator: float, denominator: float) -> float | None:
    return numerator / denominator * 100 if denominator else None


def aggregate(records: list[dict]) -> dict:
    completed = [record for record in records if record_universe(record) in {"direct_reference", "post_blockade_delivered"}]
    held = [record for record in records if record_universe(record) == "held_open"]
    tonnes = sum(number(record, "Cargo_Weight_Tons") for record in records)
    cargo_value = sum(number(record, "Cargo_Value_USD") for record in records)
    contracted = sum(number(record, "Contracted_Freight_Revenue_USD") for record in records)
    recognized = sum(number(record, "Revenue_Recognized_USD") for record in records)
    cost = sum(number(record, "Total_Cost_to_Serve_USD") for record in records)
    insurance = sum(number(record, "Insurance_Cost_USD") for record in records)
    penalty = sum(number(record, "Penalty_Cost_USD") for record in records)
    signed_sensitivity = sum(number(record, "Route_Margin_Sensitivity_USD") for record in records)
    positive_sensitivity = sum(max(number(record, "Route_Margin_Sensitivity_USD"), 0) for record in records)
    completed_delay = sum(max(number(record, "Delay_Days"), 0) for record in completed)
    held_age = sum(max(number(record, "Delay_Days"), 0) for record in held)
    planned = sum(number(record, "Planned_Transit_Days") for record in completed)
    actual = sum(number(record, "Actual_Transit_Days") for record in completed)
    difot_hits = sum(record.get("DIFOT_Met") == "Y" for record in completed)
    return {
        "shipments": len(records), "tonnes": tonnes, "cargoValue": cargo_value,
        "contractedRevenue": contracted, "recognizedRevenue": recognized, "totalCost": cost,
        "historicalContribution": recognized - cost, "signedSensitivity": signed_sensitivity,
        "positiveSensitivity": positive_sensitivity, "favourableOffset": abs(sum(min(number(record, "Route_Margin_Sensitivity_USD"), 0) for record in records)),
        "insuranceComponent": insurance, "penaltyComponent": penalty,
        "deliveredDelayDays": completed_delay, "heldAgeDays": held_age,
        "plannedTransitDays": planned, "actualTransitDays": actual,
        "averagePlannedTransitDays": planned / len(completed) if completed else None,
        "averageActualTransitDays": actual / len(completed) if completed else None,
        "difotHits": difot_hits, "difotDenominator": len(completed), "difot": ratio(difot_hits, len(completed)),
        "costPerTon": cost / tonnes if tonnes else None, "contractedRevenuePerTon": contracted / tonnes if tonnes else None,
        "insuranceBurdenPct": ratio(insurance, cargo_value), "penaltyAttributionPct": ratio(penalty, cost),
        "deliveredShipments": len(completed), "heldShipments": len(held),
    }


def percentile(values: list[float], fraction: float) -> float | None:
    ordered = sorted(values)
    if not ordered:
        return None
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * fraction
    lower, upper = math.floor(position), math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def peer_percentile(values: list[float], current: float | None) -> float | None:
    if current is None or not values:
        return None
    return sum(value <= current for value in values) / len(values) * 100


def service_interval(hits: int, sample: int) -> dict | None:
    """Return a Jeffreys posterior mean and 90% interval in percentage points."""
    if not sample:
        return None

    def beta_fraction(a: float, b: float, x: float) -> float:
        tiny = 3e-30
        qab, qap, qam = a + b, a + 1, a - 1
        c, d = 1.0, 1.0 - qab * x / qap
        d = max(abs(d), tiny) * (1 if d >= 0 else -1)
        d, h = 1 / d, 1 / d
        for m in range(1, 201):
            m2 = 2 * m
            aa = m * (b - m) * x / ((qam + m2) * (a + m2))
            d = max(abs(1 + aa * d), tiny) * (1 if 1 + aa * d >= 0 else -1)
            c = max(abs(1 + aa / c), tiny) * (1 if 1 + aa / c >= 0 else -1)
            d, c = 1 / d, c
            h *= d * c
            aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
            d = max(abs(1 + aa * d), tiny) * (1 if 1 + aa * d >= 0 else -1)
            c = max(abs(1 + aa / c), tiny) * (1 if 1 + aa / c >= 0 else -1)
            d, c = 1 / d, c
            delta = d * c
            h *= delta
            if abs(delta - 1) < 3e-14:
                break
        return h

    def beta_cdf(x: float, a: float, b: float) -> float:
        if x <= 0:
            return 0
        if x >= 1:
            return 1
        log_beta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
        factor = math.exp(a * math.log(x) + b * math.log1p(-x) + log_beta)
        if x < (a + 1) / (a + b + 2):
            return factor * beta_fraction(a, b, x) / a
        return 1 - factor * beta_fraction(b, a, 1 - x) / b

    def beta_quantile(probability: float, a: float, b: float) -> float:
        low, high = 0.0, 1.0
        for _ in range(80):
            middle = (low + high) / 2
            if beta_cdf(middle, a, b) < probability:
                low = middle
            else:
                high = middle
        return (low + high) / 2

    alpha, beta = hits + 0.5, sample - hits + 0.5
    return {"adjusted": alpha / (alpha + beta) * 100, "lower": beta_quantile(0.05, alpha, beta) * 100, "upper": beta_quantile(0.95, alpha, beta) * 100}


def group_records(records: list[dict], keys: tuple[str, ...]) -> dict[tuple, list[dict]]:
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for record in records:
        groups[tuple(record.get(key) for key in keys)].append(record)
    return groups


def build_financial_bridge(delivered: list[dict]) -> dict:
    summary = aggregate(delivered)
    direct_equivalent_cost = summary["totalCost"] - summary["signedSensitivity"]
    benchmark_contribution = summary["recognizedRevenue"] - direct_equivalent_cost
    observed_contribution = summary["recognizedRevenue"] - summary["totalCost"]
    positive_sensitivity = summary["positiveSensitivity"]
    return {
        "population": "post_blockade_delivered", "deliveredRecognizedRevenue": summary["recognizedRevenue"],
        "actualDeliveredCost": summary["totalCost"], "signedDeliveredSensitivity": summary["signedSensitivity"], "positiveDeliveredSensitivity": summary["positiveSensitivity"], "favourableOffset": summary["favourableOffset"],
        "directEquivalentCost": direct_equivalent_cost, "benchmarkContribution": benchmark_contribution,
        "observedDeliveredContribution": observed_contribution,
        "reconciliationDifference": benchmark_contribution - summary["signedSensitivity"] - observed_contribution,
        "recoveryDiagnostic": {
            "observedDeliveredLoss": abs(observed_contribution),
            "positiveDeliveredSensitivity": positive_sensitivity,
            "offsetSharePct": abs(observed_contribution) / positive_sensitivity * 100 if positive_sensitivity else None,
            "evidenceType": "DERIVED",
            "population": "post_blockade_delivered",
            "limitations": ["Historical fixed-ledger diagnostic only; not a forecasted customer recovery rate."],
        },
        "steps": [
            {"key": "deliveredRecognizedRevenue", "label": "Delivered recognized revenue", "value": summary["recognizedRevenue"], "displaySharePct": 100},
            {"key": "actualDeliveredCost", "label": "Actual delivered cost", "value": summary["totalCost"], "displaySharePct": summary["totalCost"] / summary["recognizedRevenue"] * 100 if summary["recognizedRevenue"] else None},
            {"key": "signedDeliveredSensitivity", "label": "Signed route-cost impact", "value": -summary["signedSensitivity"], "displaySharePct": summary["signedSensitivity"] / summary["recognizedRevenue"] * 100 if summary["recognizedRevenue"] else None},
            {"key": "benchmarkContribution", "label": "Direct-equivalent benchmark contribution", "value": benchmark_contribution, "displaySharePct": abs(benchmark_contribution) / summary["recognizedRevenue"] * 100 if summary["recognizedRevenue"] else None},
            {"key": "observedDeliveredContribution", "label": "Observed delivered contribution", "value": observed_contribution, "displaySharePct": abs(observed_contribution) / summary["recognizedRevenue"] * 100 if summary["recognizedRevenue"] else None},
        ],
        "evidenceType": "DERIVED", "numerator": "recognized revenue, actual cost and supplied signed sensitivity", "denominator": "post-blockade delivered shipments",
        "limitations": ["Direct is a supplied historical product-matched benchmark.", "Signed sensitivity is used as supplied; it is not a forecasted loss.", "The bridge describes the delivered historical ledger only."],
    }


def _exposure_rows(records: list[dict], dimension: str, all_records: list[dict] | None = None) -> list[dict]:
    groups = group_records(records, (dimension,))
    full_groups = group_records(all_records or records, (dimension,))
    rows = []
    for (member,), group in groups.items():
        summary = aggregate(group)
        full_summary = aggregate(full_groups.get((member,), []))
        rows.append({
            "id": f"{dimension}|{member}", "name": member, "positiveSensitivity": summary["positiveSensitivity"],
            "signedSensitivity": summary["signedSensitivity"], "favourableOffset": summary["favourableOffset"], "historicalContribution": summary["historicalContribution"],
            "contractedRevenue": summary["contractedRevenue"], "fullContractedRevenue": full_summary["contractedRevenue"],
            "recognizedRevenue": summary["recognizedRevenue"], "heldRevenue": sum(number(record, "Contracted_Freight_Revenue_USD") for record in group if record_universe(record) == "held_open"),
            "sample": summary["shipments"], "deliveredSample": summary["deliveredShipments"], "heldSample": summary["heldShipments"],
            "difot": summary["difot"], "difotHits": summary["difotHits"], "difotDenominator": summary["difotDenominator"],
            "serviceInterval": service_interval(summary["difotHits"], summary["difotDenominator"]),
            "insuranceBurdenPct": summary["insuranceBurdenPct"], "penaltyAttributionPct": summary["penaltyAttributionPct"],
            "evidenceLevel": "historical_derived", "exposurePopulation": "post_blockade_shock",
        })
    rows.sort(key=lambda item: (-item["positiveSensitivity"], item["name"]))
    total_positive = sum(item["positiveSensitivity"] for item in rows)
    cumulative = 0.0
    for rank, item in enumerate(rows, 1):
        share = item["positiveSensitivity"] / total_positive * 100 if total_positive else 0.0
        cumulative += share
        item.update({"rank": rank, "exposureSharePct": share, "cumulativeSharePct": cumulative})
    return rows


def build_customer_exposure(shock: list[dict], all_records: list[dict]) -> list[dict]:
    return _exposure_rows(shock, "Customer_Name", all_records)


def build_product_exposure(shock: list[dict]) -> list[dict]:
    return _exposure_rows(shock, "Product_Category")


def build_service_evidence(delivered: list[dict], direct: list[dict]) -> dict:
    delivered_summary, direct_summary = aggregate(delivered), aggregate(direct)
    return {
        "direct_reference": {"difot": direct_summary["difot"], "difotHits": direct_summary["difotHits"], "difotDenominator": direct_summary["difotDenominator"], "serviceInterval": service_interval(direct_summary["difotHits"], direct_summary["difotDenominator"]), "actualTransitDays": direct_summary["actualTransitDays"], "averageActualTransitDays": direct_summary["averageActualTransitDays"], "evidenceType": "DERIVED", "population": "direct_reference", "numerator": "DIFOT hits", "denominator": "completed Direct reference shipments", "limitations": ["Historical benchmark only; not a forward service promise."]},
        "post_blockade_delivered": {"difot": delivered_summary["difot"], "difotHits": delivered_summary["difotHits"], "difotDenominator": delivered_summary["difotDenominator"], "serviceInterval": service_interval(delivered_summary["difotHits"], delivered_summary["difotDenominator"]), "actualTransitDays": delivered_summary["actualTransitDays"], "averageActualTransitDays": delivered_summary["averageActualTransitDays"], "evidenceType": "DERIVED", "population": "post_blockade_delivered", "numerator": "DIFOT hits", "denominator": "completed post-blockade delivered shipments", "limitations": ["Observed service only; no unapproved lower bound is applied."]},
        "held_open": {"difot": None, "actualTransitDays": None, "difotHits": None, "difotDenominator": None, "serviceInterval": None, "evidenceType": "FACT", "population": "held_open", "limitations": ["Held shipments have no completed delivery outcome."]},
    }


def build_held_ledger(held: list[dict]) -> dict:
    summary = aggregate(held)
    rows = []
    for record in sorted(held, key=lambda item: item["Shipment_ID"]):
        tonnes, revenue, cost = number(record, "Cargo_Weight_Tons"), number(record, "Contracted_Freight_Revenue_USD"), number(record, "Total_Cost_to_Serve_USD")
        rows.append({
            "shipmentId": record["Shipment_ID"], "customer": record["Customer_Name"], "product": record["Product_Category"], "routeOrStatus": record["Route_Type"], "tonnes": tonnes,
            "revenueUnlocked": revenue, "contractedRevenue": revenue, "accruedCost": cost, "insuranceComponent": number(record, "Insurance_Cost_USD"), "penaltyComponent": number(record, "Penalty_Cost_USD"), "heldAgeDays": number(record, "Delay_Days"),
            "currentMargin": -cost, "fullLifePreFutureMargin": revenue - cost, "fullLifeGap": max(cost - revenue, 0), "optimisticIncrementalCostCeiling": revenue, "optimisticCeilingPerTon": revenue / tonnes if tonnes else None,
            "forwardContribution": None, "difot": None, "actualTransitDays": None, "evidenceLevel": "historical_fact",
        })
    return {
        "summary": {"shipments": summary["shipments"], "tonnes": summary["tonnes"], "contractedRevenue": summary["contractedRevenue"], "accruedCost": summary["totalCost"], "insuranceComponent": summary["insuranceComponent"], "penaltyComponent": summary["penaltyComponent"], "currentMargin": -summary["totalCost"], "fullLifePreFutureMargin": summary["contractedRevenue"] - summary["totalCost"], "fullLifeGap": max(summary["totalCost"] - summary["contractedRevenue"], 0), "cumulativeAgeDays": summary["heldAgeDays"], "medianAgeDays": statistics.median([number(record, "Delay_Days") for record in held]), "p90AgeDays": percentile([number(record, "Delay_Days") for record in held], 0.9), "maximumAgeDays": max(number(record, "Delay_Days") for record in held), "optimisticIncrementalCostCeiling": summary["contractedRevenue"], "optimisticCeilingPerTon": summary["contractedRevenue"] / summary["tonnes"] if summary["tonnes"] else None, "forwardContribution": None},
        "rows": rows, "evidenceType": "DERIVED", "population": "held_open", "numerator": "contracted revenue and accrued cost by Held shipment", "denominator": "Held shipment records",
        "limitations": ["This is triage evidence, not an optimized release schedule.", "Forward contribution stays null until all approved inputs are present.", "Accrued cost includes insurance and penalty components already inside total cost."],
    }


def _route_option(product: str, route: str, records: list[dict]) -> dict:
    summary = aggregate(records)
    return {"route": route, "sample": summary["shipments"], "tonnes": summary["tonnes"], "costPerTon": summary["costPerTon"], "difot": summary["difot"], "difotHits": summary["difotHits"], "difotDenominator": summary["difotDenominator"], "serviceInterval": service_interval(summary["difotHits"], summary["difotDenominator"]), "historicalContribution": summary["historicalContribution"], "positiveSensitivity": summary["positiveSensitivity"], "evidenceType": "DERIVED", "population": "post_blockade_delivered", "product": product}


def build_route_evidence(delivered: list[dict]) -> list[dict]:
    groups = group_records(delivered, ("Product_Category", "Route_Type"))
    by_product: dict[str, list[dict]] = defaultdict(list)
    for (product, route), records in groups.items():
        by_product[product].append(_route_option(product, route, records))
    output = []
    for product, options in sorted(by_product.items()):
        dominance: list[tuple[dict, list[dict]]] = []
        for candidate in options:
            dominated = [other for other in options if other["route"] != candidate["route"] and candidate["costPerTon"] <= other["costPerTon"] and candidate["difot"] >= other["difot"] and (candidate["costPerTon"] < other["costPerTon"] or candidate["difot"] > other["difot"])]
            if dominated:
                dominance.append((candidate, dominated))
        if dominance:
            candidate, dominated = max(dominance, key=lambda item: (len(item[1]), -item[0]["costPerTon"], item[0]["route"]))
            comparison = sorted(dominated, key=lambda item: (-item["costPerTon"], item["difot"], item["route"]))[0]
            status, observed_dominance = "observed_pilot_candidate", True
        else:
            candidate = min(options, key=lambda item: (item["costPerTon"], item["route"]))
            comparison = next((item for item in options if item["route"] != candidate["route"]), None)
            status, observed_dominance = "no_observed_dominance", False
        output.append({
            "id": f"product|{product}", "product": product, "candidateRoute": candidate["route"], "comparisonRoute": comparison["route"] if comparison else None,
            "candidate": candidate, "comparison": comparison, "options": sorted(options, key=lambda item: item["route"]), "status": status, "observedDominance": observed_dominance,
            "causalClaim": False, "capacityKnown": False, "liveQuoteKnown": False, "rolloutApproved": False, "approvalGates": list(ROUTE_PILOT_GATES) if observed_dominance else [], "evidenceLevel": "historical_derived",
            "limitations": ["Product-matched observational comparison only.", "Historical tonnes are not available capacity.", "Live quote, feasibility, insurance and service approvals are missing."],
        })
    return output


def _gate_names_for(postures: list[str], operational_options: list[str], universe: str) -> list[str]:
    gates: list[str] = []
    if "protect_relationship" in postures:
        gates.append("APPROVING_OWNER")
    if "renegotiate_price_or_terms" in postures:
        gates.extend(COMMERCIAL_GATES)
    if "freeze_repeat_commitment_until_gate_clears" in postures:
        gates.extend([*ROUTE_PILOT_GATES, "CUSTOMER_RECOVERY_TERM"])
    if "route_pilot" in postures or "matched_route_pilot_candidate" in operational_options:
        gates.extend(ROUTE_PILOT_GATES)
    if "insurance_structure_review" in postures:
        gates.extend(["INSURANCE_TERMS", "EFFECTIVE_DATE", "APPROVING_OWNER"])
    if universe == "held_open":
        gates.extend(HELD_RELEASE_GATES)
    return list(dict.fromkeys(gates))


def _primary_owner(postures: list[str], universe: str) -> str:
    if "renegotiate_price_or_terms" in postures or "protect_relationship" in postures:
        return "Commercial Head"
    if "insurance_structure_review" in postures:
        return "Risk/Insurance Lead"
    if "route_pilot" in postures or universe == "held_open":
        return "Supply Chain Head"
    return "Operations Head"


def _release_condition(postures: list[str], universe: str) -> str:
    if "freeze_repeat_commitment_until_gate_clears" in postures:
        return "Approved prospective unit economics are positive, route feasibility is confirmed and the approved service requirement is met."
    if "renegotiate_price_or_terms" in postures:
        return "Approved customer terms produce positive prospective unit economics."
    if "route_pilot" in postures:
        return "Live quote, feasibility, capacity, insurance and service approvals are recorded by the named owners."
    if "insurance_structure_review" in postures:
        return "Approved insurance terms and retained-loss treatment are recorded by Risk/Insurance."
    if universe == "held_open":
        return "Release requires approved quote, feasibility, capacity, insurance, service and commercial terms."
    return "No forward release condition is proposed from this historical cell alone."


def build_decision_cells(shock: list[dict], route_evidence: list[dict], customer_exposure: list[dict]) -> list[dict]:
    groups = group_records(shock, ("Customer_Name", "Product_Category", "Route_Type"))
    summaries = {key: aggregate(value) for key, value in groups.items()}
    insurance_peers = [summary["insuranceBurdenPct"] for key, summary in summaries.items() if key[2] != "Held in Gulf" and summary["insuranceBurdenPct"] is not None]
    pilot_by_product = {row["product"]: row for row in route_evidence if row["observedDominance"]}
    protected_customers = {row["name"] for row in customer_exposure[:3]}
    cells = []
    for (customer, product, route), records in groups.items():
        summary, universe = summaries[(customer, product, route)], record_universe(records[0])
        is_delivered = universe == "post_blockade_delivered"
        insurance_rank = peer_percentile(insurance_peers, summary["insuranceBurdenPct"]) if is_delivered else None
        business_problems: list[str] = []
        postures: list[str] = []
        posture_basis: dict[str, str] = {}
        operational_options: list[str] = []
        if is_delivered:
            if summary["historicalContribution"] < 0:
                business_problems.append("historical_contribution_negative")
                postures.extend(["renegotiate_price_or_terms", "freeze_repeat_commitment_until_gate_clears"])
            if summary["positiveSensitivity"] > 0:
                business_problems.append("route_cost_above_product_benchmark")
            if summary["difotHits"] < summary["difotDenominator"]:
                business_problems.append("observed_service_misses")
            if insurance_rank is not None and insurance_rank >= 75:
                business_problems.append("insurance_review_candidate")
                postures.append("insurance_structure_review")
            if customer in protected_customers:
                postures.append("protect_relationship")
                posture_basis["protect_relationship"] = "board_curated_from_exposure_pareto"
            if product in pilot_by_product:
                business_problems.append("observed_route_frontier_candidate")
                operational_options.append("matched_route_pilot_candidate")
                postures.append("route_pilot")
        else:
            business_problems.extend(["revenue_unrecognized", "delivery_outcome_open"])
            if summary["contractedRevenue"] - summary["totalCost"] < 0:
                business_problems.append("full_life_underwater_before_future_cost")
            postures.append("held_triage")
            if product in pilot_by_product:
                business_problems.append("observed_route_frontier_candidate")
                operational_options.append("matched_route_pilot_candidate")
        if not postures:
            postures.append("review_historical_evidence")
        gates = _gate_names_for(postures, operational_options, universe)
        decision_status = "blocked_missing_input" if gates else ("conditional" if operational_options else "actionable_historical")
        is_delivered = universe == "post_blockade_delivered"
        cells.append({
            "id": f"{customer}|{product}|{route}", "customer": customer, "product": product, "routeOrStatus": route, "universe": universe,
            "sample": summary["shipments"], "tonnes": summary["tonnes"], "contractedRevenue": summary["contractedRevenue"], "recognizedRevenue": summary["recognizedRevenue"], "totalCost": summary["totalCost"], "historicalContribution": summary["historicalContribution"], "signedSensitivity": summary["signedSensitivity"], "positiveSensitivity": summary["positiveSensitivity"], "favourableOffset": summary["favourableOffset"],
            "sensitivitySeverityPct": summary["positiveSensitivity"] / summary["contractedRevenue"] * 100 if is_delivered and summary["contractedRevenue"] else None,
            "zeroMarginSurcharge": max(summary["totalCost"] - summary["recognizedRevenue"], 0) if is_delivered else None, "benchmarkPreservingSurcharge": max(summary["signedSensitivity"], 0) if is_delivered else None,
            "difot": summary["difot"] if is_delivered else None, "difotHits": summary["difotHits"] if is_delivered else None, "difotDenominator": summary["difotDenominator"] if is_delivered else None, "serviceInterval": service_interval(summary["difotHits"], summary["difotDenominator"]) if is_delivered else None,
            "heldRevenue": summary["contractedRevenue"] if not is_delivered else 0.0, "heldAgeDays": summary["heldAgeDays"] if not is_delivered else None, "accruedCost": summary["totalCost"] if not is_delivered else None, "fullLifePreFutureMargin": summary["contractedRevenue"] - summary["totalCost"] if not is_delivered else None,
            "insuranceBurdenPct": summary["insuranceBurdenPct"], "penaltyAttributionPct": summary["penaltyAttributionPct"], "deliveredDelayDays": summary["deliveredDelayDays"] if is_delivered else None,
            "businessProblems": business_problems, "recommendedPostures": list(dict.fromkeys(postures)), "postureBasis": posture_basis, "operationalOptions": operational_options, "approvalGates": gates, "approvalGateDetails": [APPROVAL_GATES[name] for name in gates], "ownerRole": _primary_owner(postures, universe), "releaseCondition": _release_condition(postures, universe), "insurancePeerPercentile": insurance_rank, "evidenceLevel": "historical_derived", "decisionStatus": decision_status,
        })
    return sorted(cells, key=lambda item: (-item["positiveSensitivity"], -item["heldRevenue"], item["customer"], item["product"], item["routeOrStatus"]))


def build_decision_register(cells: list[dict], customer_exposure: list[dict]) -> list[dict]:
    customer_ids = {row["name"]: row["id"] for row in customer_exposure}
    register = []
    for index, cell in enumerate(cells, 1):
        postures = list(cell["recommendedPostures"])
        if "matched_route_pilot_candidate" in cell["operationalOptions"] and "route_pilot" not in postures:
            postures.append("route_pilot")
        register.append({
            "decisionId": f"D-{index:03d}", "scope": {"customer": cell["customer"], "product": cell["product"], "routeOrStatus": cell["routeOrStatus"]}, "cellId": cell["id"],
            "exposure": {"positiveSensitivity": cell["positiveSensitivity"], "historicalContribution": cell["historicalContribution"], "heldRevenue": cell["heldRevenue"]}, "businessProblem": list(cell["businessProblems"]), "posture": postures, "ownerRole": cell["ownerRole"],
            "horizon": {"value": "Immediate" if cell["universe"] == "held_open" or cell["historicalContribution"] < 0 else "Review", "basis": "proposal"}, "activationEvidence": list(cell["businessProblems"]), "postureBasis": dict(cell["postureBasis"]), "approvalGates": list(cell["approvalGates"]), "approvalGateDetails": list(cell["approvalGateDetails"]), "releaseCondition": cell["releaseCondition"], "evidenceLinks": [cell["id"], customer_ids.get(cell["customer"])], "evidenceLevel": "proposal", "decisionStatus": cell["decisionStatus"],
        })
    return register


def _composite_rows(records: list[dict], dimension: str) -> list[dict]:
    rows = _exposure_rows(records, dimension)
    concentration_values = [row["fullContractedRevenue"] for row in rows]
    total_concentration = sum(concentration_values)
    for row in rows:
        summary = aggregate([record for record in records if record.get(dimension) == row["name"]])
        row["M"] = summary["positiveSensitivity"] / summary["contractedRevenue"] * 100 if summary["contractedRevenue"] else 0
        row["I"] = summary["insuranceBurdenPct"] or 0
        row["D"] = summary["penaltyAttributionPct"] or 0
        row["C"] = row["fullContractedRevenue"] / total_concentration * 100 if total_concentration else 0
    for component in ("M", "I", "D", "C"):
        values = [row[component] for row in rows]
        for row in rows:
            row[component] = peer_percentile(values, row[component]) or 0
    for row in rows:
        row["compositeScore"] = 0.45 * row["M"] + 0.15 * row["I"] + 0.20 * row["D"] + 0.20 * row["C"]
    return sorted(rows, key=lambda row: (-row["compositeScore"], -row["positiveSensitivity"], row["name"]))


def build_composite_diagnostic(shock: list[dict]) -> dict:
    return {"compositeScore": {"decisionUse": False, "basis": "judgmental_policy_weights", "warning": "Do not use this score to select board priorities or exit decisions.", "weights": {"M": 0.45, "I": 0.15, "D": 0.20, "C": 0.20}, "components": {"M": "positive sensitivity / contracted revenue", "I": "insurance / cargo value", "D": "penalty / total cost", "C": "contracted-revenue concentration proxy"}, "rows": {"customers": _composite_rows(shock, "Customer_Name"), "products": _composite_rows(shock, "Product_Category")}, "evidenceType": "DERIVED", "population": "post_blockade_shock", "numerator": "rank-normalized diagnostic components", "denominator": "within-dimension peers", "limitations": ["Policy weights are judgmental.", "Dollar exposure and hard evidence flags remain the primary priority basis."]}}


def _route_rows(records: list[dict]) -> list[dict]:
    groups, shock = group_records(records, ("Route_Type",)), [record for record in records if record_universe(record) != "direct_reference"]
    shock_groups = group_records(shock, ("Route_Type",))
    total_positive = sum(max(number(record, "Route_Margin_Sensitivity_USD"), 0) for record in shock)
    rows = []
    for route in ROUTE_ORDER:
        route_records = groups.get((route,), [])
        if not route_records:
            continue
        summary, universe = aggregate(route_records), record_universe(route_records[0])
        shock_summary = aggregate(shock_groups.get((route,), [])) if route != "Direct (Pre-Blockade)" else None
        rows.append({
            "id": f"route|{route}", "routeOrStatus": route, "universe": universe, "sample": summary["shipments"], "tonnes": summary["tonnes"], "contractedRevenue": summary["contractedRevenue"], "recognizedRevenue": summary["recognizedRevenue"], "totalCost": summary["totalCost"], "historicalContribution": summary["historicalContribution"], "costPerTon": summary["costPerTon"], "positiveSensitivity": shock_summary["positiveSensitivity"] if shock_summary else None, "signedSensitivity": shock_summary["signedSensitivity"] if shock_summary else None, "favourableOffset": shock_summary["favourableOffset"] if shock_summary else None, "exposureSharePct": shock_summary["positiveSensitivity"] / total_positive * 100 if shock_summary and total_positive else None,
            "difot": summary["difot"] if universe != "held_open" else None, "difotHits": summary["difotHits"] if universe != "held_open" else None, "difotDenominator": summary["difotDenominator"] if universe != "held_open" else None, "serviceInterval": service_interval(summary["difotHits"], summary["difotDenominator"]) if universe != "held_open" else None, "deliveredDelayDays": summary["deliveredDelayDays"] if universe != "held_open" else None, "heldAgeDays": summary["heldAgeDays"] if universe == "held_open" else None, "averageActualTransitDays": summary["averageActualTransitDays"] if universe != "held_open" else None, "insuranceBurdenPct": summary["insuranceBurdenPct"], "penaltyAttributionPct": summary["penaltyAttributionPct"], "evidenceLevel": "historical_derived",
        })
    return rows


def _concentration_diagnostics(records: list[dict], dimension: str, sensitivity: bool = False) -> dict:
    groups = group_records(records, (dimension,))
    values = []
    for (member,), group in groups.items():
        amount = sum(max(number(record, "Route_Margin_Sensitivity_USD"), 0) for record in group) if sensitivity else sum(number(record, "Contracted_Freight_Revenue_USD") for record in group)
        values.append((member, amount))
    total = sum(amount for _, amount in values)
    shares = [amount / total for _, amount in values] if total else []
    hhi = sum(share * share for share in shares)
    return {"hhi": hhi, "effectiveNumber": 1 / hhi if hhi else None}


def build_dashboard(records: list[dict], source_info: dict, source_validation: dict | None = None) -> dict:
    classified = classify_records(records)
    direct, delivered, held = classified["direct_reference"], classified["post_blockade_delivered"], classified["held_open"]
    shock = [*delivered, *held]
    portfolio_summary, shock_summary = aggregate(records), aggregate(shock)
    direct_summary, delivered_summary, held_summary = aggregate(direct), aggregate(delivered), aggregate(held)
    customer_exposure = build_customer_exposure(shock, records)
    product_exposure = build_product_exposure(shock)
    route_evidence = build_route_evidence(delivered)
    decision_cells = build_decision_cells(shock, route_evidence, customer_exposure)
    financial_bridge, held_ledger = build_financial_bridge(delivered), build_held_ledger(held)
    service = build_service_evidence(delivered, direct)
    metadata = {
        "sourceFile": source_info["sourceFile"], "sourceSheet": source_info["sourceSheet"], "sourceRows": len(records), "uniqueShipmentIds": len({record.get("Shipment_ID") for record in records}), "observationStart": min(record["Departure_Date"] for record in records), "observationEnd": max(record["Departure_Date"] for record in records), "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"), "sourceStatus": "accepted" if not source_validation or source_validation["pass"] else "rejected", "sourceSha256": source_info.get("sourceSha256"),
    }
    universes = {
        "direct_reference": {"rows": len(direct), "use": "historical product-matched benchmark", "evidenceType": "FACT", "population": "direct_reference", "limitations": ["Not a forward quote or capacity assumption."]},
        "post_blockade_delivered": {"rows": len(delivered), "use": "realized disruption economics and completed service", "evidenceType": "FACT", "population": "post_blockade_delivered", "limitations": ["Observed historical outcomes only."]},
        "held_open": {"rows": len(held), "use": "undelivered revenue and accrued-cost ledger", "evidenceType": "FACT", "population": "held_open", "limitations": ["No completed service outcome or release schedule."]},
    }
    portfolio = {
        "shipments": portfolio_summary["shipments"], "tonnes": portfolio_summary["tonnes"], "contractedRevenue": portfolio_summary["contractedRevenue"], "recognizedRevenue": portfolio_summary["recognizedRevenue"], "heldContractedRevenue": held_summary["contractedRevenue"], "totalCost": portfolio_summary["totalCost"], "historicalContribution": portfolio_summary["historicalContribution"], "signedSensitivity": shock_summary["signedSensitivity"], "positiveSensitivity": shock_summary["positiveSensitivity"], "favourableOffset": shock_summary["favourableOffset"], "revenueIdentityDifference": portfolio_summary["contractedRevenue"] - portfolio_summary["recognizedRevenue"] - held_summary["contractedRevenue"], "directReference": direct_summary, "postBlockadeDelivered": delivered_summary, "heldOpen": held_summary, "evidenceType": "DERIVED", "population": "all accepted shipment records for portfolio; post_blockade_shock for route sensitivity", "numerator": "summed source monetary fields", "denominator": "accepted shipment records", "limitations": ["Historical contribution is not a forward forecast.", "Total cost already includes freight, fuel, insurance and penalty."],
    }
    methodology = {
        "evidenceLabels": {"FACT": "Directly observed in the accepted workbook.", "DERIVED": "Calculated from accepted workbook fields using documented formulas.", "PROPOSAL": "A management posture or owner assignment, not an observed outcome.", "MISSING_INPUT": "Required for prospective execution and not supplied in the workbook."},
        "financialBridge": {"evidenceType": "DERIVED", "population": "post_blockade_delivered", "numerator": "recognized revenue less cost with supplied signed sensitivity", "denominator": "delivered recognized revenue", "limitations": ["No future pricing or recovery is assumed."]},
        "exposure": {"evidenceType": "DERIVED", "population": "post_blockade_shock", "numerator": "positive supplied Route_Margin_Sensitivity_USD", "denominator": "total positive shock sensitivity", "limitations": ["Positive sensitivity is route-cost exposure, not an accounting loss."]},
        "service": {"evidenceType": "DERIVED", "population": "completed shipments only", "numerator": "DIFOT hits", "denominator": "completed shipments in the named universe", "limitations": ["Held shipments are excluded from DIFOT."]},
        "heldLedger": {"evidenceType": "DERIVED", "population": "held_open", "numerator": "contracted revenue, accrued cost and Held age", "denominator": "Held shipment records", "limitations": ["Forward contribution is null until approved inputs are supplied."]},
        "routeEvidence": {"evidenceType": "DERIVED", "population": "post_blockade_delivered grouped by product and route", "numerator": "observed cost/t and DIFOT comparison", "denominator": "product-matched observed route groups", "limitations": ["No causal, optimal, capacity-feasible or rollout-approved claim."]},
        "decisionCells": {"evidenceType": "DERIVED", "population": "observed post-blockade customer × product × route/status cells", "numerator": "cell-level historical metrics and hard evidence flags", "denominator": "44 observed cells", "limitations": ["Prospective action remains conditional on named approval gates."]},
        "decisionRegister": {"evidenceType": "PROPOSAL", "population": "decision cells", "numerator": "historical activation evidence", "denominator": "named decision cell", "limitations": ["No permanent exit or rollout approval is generated."]},
        "approvalGates": list(APPROVAL_GATES.values()),
        "limitations": ["The engine is historical evidence and decision gating, not a route optimizer.", "Historical route tonnage is not available capacity.", "Missing forward inputs are rendered as open rather than estimated."],
    }
    dashboard = {
        "schemaVersion": SCHEMA_VERSION, "metadata": metadata, "qa": {}, "universes": universes, "financialBridge": financial_bridge, "portfolio": portfolio,
        "routes": _route_rows(records), "customers": customer_exposure, "products": product_exposure, "decisionCells": decision_cells, "heldLedger": held_ledger,
        "routeEvidence": route_evidence, "decisionRegister": build_decision_register(decision_cells, customer_exposure), "appendixDiagnostics": build_composite_diagnostic(shock), "methodology": methodology, "serviceEvidence": service,
        "concentration": {"customerRevenue": _concentration_diagnostics(records, "Customer_Name"), "routeSensitivity": _concentration_diagnostics(shock, "Route_Type", sensitivity=True), "productSensitivity": _concentration_diagnostics(shock, "Product_Category", sensitivity=True)},
    }
    return clean_number(dashboard)


def _recursive_values(payload):
    if isinstance(payload, dict):
        for key, value in payload.items():
            yield key, value
            yield from _recursive_values(value)
    elif isinstance(payload, list):
        for value in payload:
            yield from _recursive_values(value)


def run_qa(records: list[dict], dashboard: dict, source_validation: dict) -> dict:
    classified = classify_records(records)
    direct, delivered, held = classified["direct_reference"], classified["post_blockade_delivered"], classified["held_open"]
    shock = [*delivered, *held]
    portfolio, direct_summary, delivered_summary, held_summary = aggregate(records), aggregate(direct), aggregate(delivered), aggregate(held)
    all_row_arithmetic, unit_economics, row_failures = True, True, []
    for record in records:
        total_cost = number(record, "Total_Cost_to_Serve_USD")
        component_cost = sum(number(record, field) for field in ("Freight_Cost_USD", "Fuel_Cost_USD", "Insurance_Cost_USD", "Penalty_Cost_USD"))
        if abs(total_cost - component_cost) >= EPSILON_CENTS:
            all_row_arithmetic, _ = False, row_failures.append(f"{record['Shipment_ID']}: cost_components")
        if abs(number(record, "Gross_Margin_USD") - (number(record, "Revenue_Recognized_USD") - total_cost)) >= EPSILON_CENTS:
            all_row_arithmetic, _ = False, row_failures.append(f"{record['Shipment_ID']}: gross_margin")
        tonnes = number(record, "Cargo_Weight_Tons")
        if tonnes and abs(total_cost / tonnes - number(record, "Cost_per_Ton_USD")) >= EPSILON_CENTS:
            unit_economics, _ = False, row_failures.append(f"{record['Shipment_ID']}: cost_per_ton")
        if tonnes and abs(number(record, "Contracted_Freight_Revenue_USD") / tonnes - number(record, "Revenue_per_Ton_USD")) >= EPSILON_CENTS:
            unit_economics, _ = False, row_failures.append(f"{record['Shipment_ID']}: revenue_per_ton")
    cells, register, route_evidence = dashboard["decisionCells"], dashboard["decisionRegister"], dashboard["routeEvidence"]
    top_level_keys = {"schemaVersion", "metadata", "qa", "universes", "financialBridge", "portfolio", "routes", "customers", "products", "decisionCells", "heldLedger", "routeEvidence", "decisionRegister", "appendixDiagnostics", "methodology", "serviceEvidence", "concentration"}
    forbidden_keys = {"scenarios", "scenarioInputs", "scenarioContribution", "scenarioDIFOT", "unservedTonnes", "optionUtilization", "costMultiplier", "insuranceMultiplier", "penaltyMultiplier", "clearRate", "heldInflowMultiplier", "recoveryRate", "serviceMultiplier", "unavailableRoutes"}
    all_keys = {key for key, _ in _recursive_values(dashboard)}
    source_checks = {"rowCount243": source_validation["checks"]["rowCount"], "requiredColumnsPresent": source_validation["checks"]["requiredColumns"], "uniqueNonblankShipmentIds243": source_validation["checks"]["uniqueShipmentIds"] and source_validation["checks"]["nonblankShipmentIds"], "numericFieldsParse": source_validation["checks"]["numericFieldsParse"]}
    universe_checks = {"direct51Delivered138Held54": len(direct) == 51 and len(delivered) == 138 and len(held) == 54, "universeTotal243": len(direct) + len(delivered) + len(held) == 243, "completedServiceFieldsPresent": all(record.get("Actual_Transit_Days") is not None for record in [*direct, *delivered]), "heldRecognizedRevenueZero": all(number(record, "Revenue_Recognized_USD") == 0 for record in held), "heldActualTransitMissing": all(record.get("Actual_Transit_Days") is None for record in held)}
    aggregate_checks = {"contractedRevenueIdentity": abs(portfolio["contractedRevenue"] - portfolio["recognizedRevenue"] - held_summary["contractedRevenue"]) < EPSILON_CENTS, "deliveredContributionIdentity": abs(delivered_summary["historicalContribution"] - (delivered_summary["recognizedRevenue"] - delivered_summary["totalCost"])) < EPSILON_CENTS, "financialBridgeReconciles": abs(dashboard["financialBridge"]["reconciliationDifference"]) < EPSILON_CENTS, "customerExposureReconciles": abs(sum(row["positiveSensitivity"] for row in dashboard["customers"]) - sum(max(number(record, "Route_Margin_Sensitivity_USD"), 0) for record in shock)) < EPSILON_CENTS, "productExposureReconciles": abs(sum(row["positiveSensitivity"] for row in dashboard["products"]) - sum(max(number(record, "Route_Margin_Sensitivity_USD"), 0) for record in shock)) < EPSILON_CENTS, "routeExposureReconciles": abs(sum(row["positiveSensitivity"] or 0 for row in dashboard["routes"] if row["universe"] != "direct_reference") - sum(max(number(record, "Route_Margin_Sensitivity_USD"), 0) for record in shock)) < EPSILON_CENTS, "decisionCells44": len(cells) == 44, "decisionCellRowsReconcile": sum(cell["sample"] for cell in cells) == len(shock), "heldLedger54": dashboard["heldLedger"]["summary"]["shipments"] == 54 and len(dashboard["heldLedger"]["rows"]) == 54}
    service_checks = {"directDIFOT51of51": direct_summary["difotHits"] == 51 and direct_summary["difotDenominator"] == 51, "postBlockadeDIFOT113of138": delivered_summary["difotHits"] == 113 and delivered_summary["difotDenominator"] == 138, "heldDIFOTNull": dashboard["serviceEvidence"]["held_open"]["difot"] is None and dashboard["serviceEvidence"]["held_open"]["actualTransitDays"] is None, "intervalBoundsValid": all(interval is None or 0 <= interval["lower"] <= interval["adjusted"] <= interval["upper"] <= 100 for interval in [dashboard["serviceEvidence"]["direct_reference"]["serviceInterval"], dashboard["serviceEvidence"]["post_blockade_delivered"]["serviceInterval"], *[row["serviceInterval"] for row in dashboard["routes"]], *[cell["serviceInterval"] for cell in cells]])}
    decision_checks = {"everyDecisionReferencesCell": all(item["cellId"] in {cell["id"] for cell in cells} for item in register), "prospectiveActionsListGates": all(not (set(item["posture"]) & {"renegotiate_price_or_terms", "freeze_repeat_commitment_until_gate_clears", "route_pilot", "insurance_structure_review", "held_triage"}) or item["approvalGates"] for item in register), "noPermanentExitAction": not any("exit_customer" in str(item).lower() or "stop_lane_permanently" in str(item).lower() for item in register), "noRouteRolloutApproved": all(item["rolloutApproved"] is False for item in route_evidence), "noDecisionUsesComposite": not any("composite" in str(item).lower() for item in [*cells, *register]), "heldForwardContributionNull": all(row["forwardContribution"] is None for row in dashboard["heldLedger"]["rows"]) and dashboard["heldLedger"]["summary"]["forwardContribution"] is None}
    contract_checks = {"schemaVersion2": dashboard.get("schemaVersion") == SCHEMA_VERSION, "requiredTopLevelKeys": top_level_keys.issubset(dashboard.keys()), "noForbiddenKeys": not forbidden_keys.intersection(all_keys), "stableUniqueCellIds": len({cell["id"] for cell in cells}) == len(cells), "numericNullDiscipline": dashboard["serviceEvidence"]["held_open"]["difot"] is None and all(cell["difot"] is None for cell in cells if cell["universe"] == "held_open"), "noDeprecatedSourceFields": not any(key in all_keys for key in {"STATED_ROWS", "caseStatedRows", "provisional", "duplicatePolicy"})}
    groups = {"source": source_checks, "universes": universe_checks, "rowArithmetic": {"costComponentReconciliation": all_row_arithmetic, "marginReconciliation": all_row_arithmetic, "weightedUnitEconomics": unit_economics}, "aggregate": aggregate_checks, "service": service_checks, "decisions": decision_checks, "contract": contract_checks}
    failures = []
    populations = {"source": "accepted workbook", "universes": "direct_reference, post_blockade_delivered, held_open", "rowArithmetic": "all 243 shipment records", "aggregate": "portfolio and generated ledgers", "service": "completed service and Held-open records", "decisions": "decision cells, register and route evidence", "contract": "generated dashboard JSON"}
    for group_name, checks in groups.items():
        for check_name, passed in checks.items():
            if not passed:
                failures.append({"name": f"{group_name}.{check_name}", "population": populations[group_name], "detail": "check returned false"})
    return {"schemaVersion": SCHEMA_VERSION, "pass": not failures, "analyticalChecksPass": not failures, "failedChecks": failures, "groups": groups, "counts": {"sourceRows": len(records), "uniqueShipmentIds": len({record.get("Shipment_ID") for record in records}), "directReferenceRows": len(direct), "postBlockadeDeliveredRows": len(delivered), "heldOpenRows": len(held), "decisionCells": len(cells), "decisionRegisterRows": len(register)}, "golden": {"contractedRevenue": portfolio["contractedRevenue"], "recognizedRevenue": portfolio["recognizedRevenue"], "heldRevenue": held_summary["contractedRevenue"], "deliveredCost": delivered_summary["totalCost"], "deliveredSignedSensitivity": delivered_summary["signedSensitivity"], "benchmarkContribution": dashboard["financialBridge"]["benchmarkContribution"], "observedDeliveredContribution": dashboard["financialBridge"]["observedDeliveredContribution"], "heldCost": held_summary["totalCost"], "heldPenalty": held_summary["penaltyComponent"], "heldInsurance": held_summary["insuranceComponent"], "heldFullLifeGap": dashboard["heldLedger"]["summary"]["fullLifeGap"], "directDIFOT": direct_summary["difot"], "postBlockadeDIFOT": delivered_summary["difot"], "topThreeCustomerExposureShare": dashboard["customers"][2]["cumulativeSharePct"], "topTwoProductExposureShare": dashboard["products"][1]["cumulativeSharePct"]}}


def clean_number(value_to_clean):
    if isinstance(value_to_clean, float) and not math.isfinite(value_to_clean):
        return None
    if isinstance(value_to_clean, dict):
        return {key: clean_number(value) for key, value in value_to_clean.items()}
    if isinstance(value_to_clean, list):
        return [clean_number(value) for value in value_to_clean]
    return value_to_clean


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workbook", type=Path, default=DEFAULT_WORKBOOK)
    parser.add_argument("--dashboard", type=Path, default=DASHBOARD_PATH)
    parser.add_argument("--qa", type=Path, default=QA_PATH)
    parser.add_argument("--strict-source", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--strict-board", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        records, source_info = parse_workbook(args.workbook)
        source_validation = validate_source(records, source_info)
        if not source_validation["pass"]:
            raise ValueError("source validation failed: " + ", ".join(source_validation["failedChecks"]) + (f"; missing columns: {source_validation['missingColumns']}" if source_validation["missingColumns"] else ""))
        dashboard = build_dashboard(records, source_info, source_validation)
        qa = run_qa(records, dashboard, source_validation)
        dashboard["qa"] = qa
        write_json(args.dashboard, dashboard)
        write_json(args.qa, qa)
    except (KeyError, OSError, ET.ParseError, ValueError, BadZipFile) as error:
        print(f"analysis failed: {error}", file=sys.stderr)
        return 1
    if not qa["pass"]:
        print("QA failed: " + ", ".join(item["name"] for item in qa["failedChecks"]), file=sys.stderr)
        return 1
    print(f"Generated {args.dashboard} and {args.qa}: {qa['counts']['sourceRows']} accepted rows, {qa['counts']['decisionCells']} decision cells, {qa['counts']['heldOpenRows']} Held rows.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
