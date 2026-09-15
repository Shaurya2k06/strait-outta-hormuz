#!/usr/bin/env python3
"""Build the dashboard data from the supplied workbook.

The workbook is parsed with the standard library so refreshes do not depend on
an analysis package being installed.  The script writes the UI data and a QA
report, and exits non-zero when a reconciliation check fails.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from zipfile import BadZipFile, ZipFile
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WORKBOOK = ROOT / "R2-WAR ROOM MASTERPLAN-cleaned.xlsx"
DASHBOARD_PATH = ROOT / "client/src/dashboard-data.json"
QA_PATH = ROOT / "analysis/qa-report.json"
SOURCE_MANIFEST_PATH = ROOT / "analysis/source-manifest.json"
DUPLICATE_ADJUDICATION_PATH = ROOT / "analysis/duplicate-adjudication.json"
FORWARD_INPUTS_PATH = ROOT / "analysis/forward-inputs.json"
SOURCE_CONTRACT_VERSION = "source-contract-v1"
FORWARD_CONTRACT_VERSION = "forward-ledger-v1"
APPROVED_RAW_ROWS = 243
EXPECTED_CANONICAL_ROWS = 243
EXPECTED_DUPLICATE_EXCESS = 0
STATED_ROWS = EXPECTED_CANONICAL_ROWS
FORWARD_ROUTES = {
    "Cape of Good Hope",
    "Pipeline Bypass",
    "Overland Truck",
    "Air Bridge",
}
PROPOSAL_ROUTE_INPUTS = {
    "Cape of Good Hope": {
        "capacityTonnes": 4_000_000,
        "costPerTon": 18.0,
        "insuranceRate": 0.018,
        "serviceLowerBound": 0.67,
        "expectedFuturePenaltyPerTon": 0.0,
        "failureCostPerTon": 1.0,
        "recoverableSurchargePerTon": 0.0,
        "cargoTypes": ["Container (TEU)", "Bulk Liquid (Chem Tanker)", "Bulk Liquid (VLCC)"],
    },
    "Pipeline Bypass": {
        "capacityTonnes": 2_000_000,
        "costPerTon": 11.0,
        "insuranceRate": 0.012,
        "serviceLowerBound": 0.82,
        "expectedFuturePenaltyPerTon": 0.0,
        "failureCostPerTon": 0.7,
        "recoverableSurchargePerTon": 0.0,
        "cargoTypes": ["Bulk Liquid (Chem Tanker)", "Bulk Liquid (VLCC)"],
    },
    "Overland Truck": {
        "capacityTonnes": 850_000,
        "costPerTon": 95.0,
        "insuranceRate": 0.01,
        "serviceLowerBound": 0.78,
        "expectedFuturePenaltyPerTon": 0.0,
        "failureCostPerTon": 1.2,
        "recoverableSurchargePerTon": 0.0,
        "cargoTypes": ["Container (TEU)"],
    },
    "Air Bridge": {
        "capacityTonnes": 35_000,
        "costPerTon": 1_250.0,
        "insuranceRate": 0.008,
        "serviceLowerBound": 0.9,
        "expectedFuturePenaltyPerTon": 0.0,
        "failureCostPerTon": 0.8,
        "recoverableSurchargePerTon": 0.0,
        "cargoTypes": ["Container (TEU)"],
    },
}

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS = {"m": MAIN_NS}

TEXT_FIELDS = {
    "Shipment_ID",
    "Departure_Date",
    "Route_Type",
    "Product_Category",
    "Cargo_Type",
    "Customer_Name",
    "Customer_Region",
    "DIFOT_Met",
}

ROUTE_LABELS = {
    "Direct (Pre-Blockade)": "Direct / benchmark",
    "Cape of Good Hope": "Cape of Good Hope",
    "Pipeline Bypass": "Pipeline Bypass",
    "Overland Truck": "Overland Truck",
    "Air Bridge": "Air Bridge",
    "Held in Gulf": "Held in Gulf",
}

SCENARIO_DEFINITIONS = [
    {
        "name": "Normalization",
        "tone": "mint",
        "detail": "Disruption days decline; routes, capacity, current quotes and insurance ease.",
        "inputs": {
            "costMultiplier": 0.9,
            "insuranceMultiplier": 0.8,
            "penaltyMultiplier": 0.6,
            "clearRate": 0.75,
            "heldInflowMultiplier": 0.5,
            "recoveryRate": 0.7,
            "serviceMultiplier": 1.02,
            "unavailableRoutes": [],
        },
        "action": "Keep controls until release metrics clear.",
    },
    {
        "name": "Prolonged disruption",
        "tone": "amber",
        "detail": "Current alternatives persist; capacity, delay, fuel and insurance step up.",
        "inputs": {
            "costMultiplier": 1.15,
            "insuranceMultiplier": 1.2,
            "penaltyMultiplier": 1.3,
            "clearRate": 0.35,
            "heldInflowMultiplier": 1.25,
            "recoveryRate": 0.4,
            "serviceMultiplier": 0.96,
            "unavailableRoutes": [],
        },
        "action": "Extend only dated exceptions that clear the live hurdle.",
    },
    {
        "name": "Escalation / next chokepoint",
        "tone": "red",
        "detail": "Pipeline capacity or one insurer is unavailable; Held inflow grows.",
        "inputs": {
            "costMultiplier": 1.35,
            "insuranceMultiplier": 1.4,
            "penaltyMultiplier": 1.6,
            "clearRate": 0.15,
            "heldInflowMultiplier": 1.5,
            "recoveryRate": 0.2,
            "serviceMultiplier": 0.82,
            "unavailableRoutes": ["Pipeline Bypass"],
        },
        "action": "Exercise options; pause unrecovered commitments.",
    },
]

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
    if cell.attrib.get("t") == "s":
        return shared_strings[int(raw)]
    return raw


def parse_workbook(path: Path) -> tuple[list[dict], dict]:
    with ZipFile(path) as archive:
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            shared_strings = [
                "".join(item.text or "" for item in string.iter(f"{{{MAIN_NS}}}t"))
                for string in root
            ]

        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        relation_map = {item.attrib["Id"]: item.attrib["Target"] for item in relationships}
        shipment_sheet = next(
            sheet
            for sheet in workbook.findall("m:sheets/m:sheet", NS)
            if sheet.attrib["name"] == "Shipment_Data"
        )
        relation_id = shipment_sheet.attrib[f"{{{REL_NS}}}id"]
        sheet_target = relation_map[relation_id]
        sheet_path = f"xl/{sheet_target.lstrip('/')}"
        sheet = ET.fromstring(archive.read(sheet_path))
        rows = sheet.findall(".//m:row", NS)

        def values(row: ET.Element) -> list[str]:
            result = [""] * 31
            for cell in row.findall("m:c", NS):
                result[column_number(cell.attrib.get("r", ""))] = cell_value(cell, shared_strings)
            return result

        header_values = values(rows[0])
        headers = [header for header in header_values if header]
        numeric_fields = set(headers) - TEXT_FIELDS
        parsed = []
        for row in rows[1:]:
            values_by_column = values(row)
            record = {header: values_by_column[index] for index, header in enumerate(header_values) if header}
            for field in numeric_fields:
                raw = record.get(field, "")
                if raw in (None, ""):
                    record[field] = None
                else:
                    record[field] = float(raw)
            parsed.append(record)

    source_bytes = path.read_bytes()
    return parsed, {
        "sheet": "Shipment_Data",
        "columns": headers,
        "sourceRows": len(parsed),
        "sourceFile": path.name,
        "sourceSha256": hashlib.sha256(source_bytes).hexdigest(),
        "sourceSizeBytes": len(source_bytes),
    }


def normalized_record(record: dict) -> tuple:
    return tuple(
        (key, round(value, 9) if isinstance(value, float) else value)
        for key, value in sorted(record.items())
    )


def canonicalize(records: list[dict]) -> tuple[list[dict], dict]:
    by_id: dict[str, list[dict]] = defaultdict(list)
    blank_ids = []
    for row_number, record in enumerate(records, 2):
        shipment_id = str(record.get("Shipment_ID") or "").strip()
        if not shipment_id:
            blank_ids.append(row_number)
            continue
        record["Shipment_ID"] = shipment_id
        by_id[shipment_id].append(record)

    canonical = []
    exact_duplicates = []
    conflicts = []
    for shipment_id, group in by_id.items():
        if len(group) == 1:
            canonical.append(group[0])
            continue
        if len({normalized_record(record) for record in group}) == 1:
            exact_duplicates.append({"shipmentId": shipment_id, "rows": len(group)})
            canonical.append(group[0])
            continue
        differing_fields = [
            field
            for field in group[0]
            if len({record.get(field) for record in group}) > 1
        ]
        conflicts.append({"shipmentId": shipment_id, "rows": len(group), "fields": differing_fields})

    duplicate_excess_rows = sum(max(item["rows"] - 1, 0) for item in exact_duplicates)
    adjudication_table = [
        {
            "shipmentId": item["shipmentId"],
            "rawRows": item["rows"],
            "canonicalRows": 1,
            "excessRows": item["rows"] - 1,
            "decision": "collapse_exact_duplicate",
        }
        for item in exact_duplicates
    ]
    return canonical, {
        "duplicateGroups": len(exact_duplicates) + len(conflicts),
        "exactDuplicatesCollapsed": exact_duplicates,
        "conflicts": conflicts,
        "blankShipmentIdRows": blank_ids,
        "duplicateExcessRows": duplicate_excess_rows,
        "adjudicationTable": adjudication_table,
    }


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as file:
        payload = json.load(file)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def source_gate_status(source_info: dict, duplicate_info: dict, canonical_rows: int, manifest: dict) -> dict:
    expected_raw_rows = manifest.get("approvedRawRows", APPROVED_RAW_ROWS)
    expected_canonical_rows = manifest.get("expectedCanonicalRows", EXPECTED_CANONICAL_ROWS)
    expected_duplicate_excess = manifest.get("expectedDuplicateExcessRows", EXPECTED_DUPLICATE_EXCESS)
    expected_duplicate_ids = sorted(manifest.get("expectedExactDuplicateShipmentIds", []))
    actual_duplicate_ids = sorted(
        item["shipmentId"] for item in duplicate_info["exactDuplicatesCollapsed"]
    )
    expected_hash = manifest.get("approvedSha256")
    checks = {
        "approvedRawRows": source_info["sourceRows"] == expected_raw_rows,
        "canonicalRows": canonical_rows == expected_canonical_rows,
        "duplicateExcessRows": duplicate_info["duplicateExcessRows"] == expected_duplicate_excess,
        "noBlankShipmentIds": not duplicate_info["blankShipmentIdRows"],
        "noConflictingDuplicates": not duplicate_info["conflicts"],
        "duplicateAdjudicationMatchesManifest": actual_duplicate_ids == expected_duplicate_ids,
        "approvedWorkbookHash": bool(expected_hash) and source_info["sourceSha256"] == expected_hash,
        "approvedSourceVersion": source_info["sourceFile"] == manifest.get("approvedRawSourceFile"),
        "sourceContractVersion": manifest.get("contractVersion") == SOURCE_CONTRACT_VERSION,
    }
    reasons = {
        name: (
            "pass"
            if passed
            else {
                "approvedRawRows": f"expected {expected_raw_rows} raw rows; found {source_info['sourceRows']}",
                "canonicalRows": f"expected {expected_canonical_rows} canonical rows; found {canonical_rows}",
                "duplicateExcessRows": (
                    f"expected {expected_duplicate_excess} duplicate excess rows; "
                    f"found {duplicate_info['duplicateExcessRows']}"
                ),
                "noBlankShipmentIds": "blank Shipment_ID rows require adjudication",
                "noConflictingDuplicates": "conflicting duplicate Shipment_ID fields require adjudication",
                "duplicateAdjudicationMatchesManifest": (
                    f"expected duplicate IDs {expected_duplicate_ids}; found {actual_duplicate_ids}"
                ),
                "approvedWorkbookHash": "approvedSha256 is missing or does not match the workbook",
                "approvedSourceVersion": (
                    f"expected approved source {manifest.get('approvedRawSourceFile')}; "
                    f"found {source_info['sourceFile']}"
                ),
                "sourceContractVersion": f"expected {SOURCE_CONTRACT_VERSION}",
            }[name]
        )
        for name, passed in checks.items()
    }
    return {
        "pass": all(checks.values()),
        "status": "verified" if all(checks.values()) else "unverified",
        "checks": checks,
        "reasons": reasons,
        "approvedRawRows": expected_raw_rows,
        "expectedCanonicalRows": expected_canonical_rows,
        "expectedDuplicateExcessRows": expected_duplicate_excess,
        "observedRawRows": source_info["sourceRows"],
        "observedCanonicalRows": canonical_rows,
        "observedDuplicateExcessRows": duplicate_info["duplicateExcessRows"],
        "approvedSourceFile": manifest.get("approvedRawSourceFile"),
        "observedSourceFile": source_info["sourceFile"],
        "observedSha256": source_info["sourceSha256"],
    }


def forward_input_status(payload: dict) -> dict:
    routes = payload.get("routes") if isinstance(payload.get("routes"), dict) else {}
    required_route_fields = (
        "capacityTonnes",
        "costPerTon",
        "insuranceRate",
        "serviceLowerBound",
        "expectedFuturePenaltyPerTon",
        "failureCostPerTon",
        "recoverableSurchargePerTon",
    )
    def valid_route(route: dict) -> bool:
        if not isinstance(route, dict) or not all(route.get(field) is not None for field in required_route_fields):
            return False
        if not all(isinstance(route[field], (int, float)) and math.isfinite(route[field]) for field in required_route_fields):
            return False
        return (
            route["capacityTonnes"] >= 0
            and route["costPerTon"] >= 0
            and 0 <= route["insuranceRate"] <= 1
            and 0 <= route["serviceLowerBound"] <= 1
            and route["expectedFuturePenaltyPerTon"] >= 0
            and route["failureCostPerTon"] >= 0
            and route["recoverableSurchargePerTon"] >= 0
            and bool(route.get("cargoTypes"))
        )

    complete = bool(routes) and set(routes) == FORWARD_ROUTES and all(valid_route(route) for route in routes.values())
    approved = payload.get("approved") is True
    versioned = payload.get("contractVersion") == FORWARD_CONTRACT_VERSION
    has_source = bool(payload.get("source"))
    has_effective_date = bool(payload.get("effectiveDate"))
    ready = approved and complete and versioned and has_source and has_effective_date
    return {
        "ready": ready,
        "status": "verified" if ready else "awaiting owner approval",
        "approved": approved,
        "complete": complete,
        "versioned": versioned,
        "hasSource": has_source,
        "hasEffectiveDate": has_effective_date,
        "source": payload.get("source", "missing"),
        "effectiveDate": payload.get("effectiveDate"),
        "requiredFields": [
            "approved owner-supplied route-week capacity",
            "quoted incremental freight and fuel",
            "incremental insurance rate",
            "expected future penalty and failure cost",
            "service lower bound",
            "recoverable surcharge / price term",
            "route-week capacity or an approved horizon capacity",
        ],
    }


def classify(record: dict) -> str:
    route = record["Route_Type"]
    if route.startswith("Direct"):
        return "reference"
    if route == "Held in Gulf":
        return "held"
    return "delivered"


def value(record: dict, field: str) -> float:
    return record.get(field) or 0.0


def aggregate(records: list[dict]) -> dict:
    completed = [record for record in records if record["kind"] in {"delivered", "reference"}]
    held = [record for record in records if record["kind"] == "held"]
    tonnes = sum(value(record, "Cargo_Weight_Tons") for record in records)
    cargo_value = sum(value(record, "Cargo_Value_USD") for record in records)
    contracted = sum(value(record, "Contracted_Freight_Revenue_USD") for record in records)
    recognized = sum(value(record, "Revenue_Recognized_USD") for record in records)
    cost = sum(value(record, "Total_Cost_to_Serve_USD") for record in records)
    signed = sum(value(record, "Route_Margin_Sensitivity_USD") for record in records)
    adverse = sum(max(value(record, "Route_Margin_Sensitivity_USD"), 0) for record in records)
    delay = sum(max(value(record, "Delay_Days"), 0) for record in completed)
    planned = sum(value(record, "Planned_Transit_Days") for record in completed)
    actual = sum(value(record, "Actual_Transit_Days") for record in completed)
    difot_hits = sum(record.get("DIFOT_Met") == "Y" for record in completed)

    def ratio(numerator: float, denominator: float) -> float | None:
        return numerator / denominator * 100 if denominator else None

    return {
        "shipments": len(records),
        "tonnes": tonnes,
        "cargoValue": cargo_value,
        "contracted": contracted,
        "recognized": recognized,
        "cost": cost,
        "grossMargin": recognized - cost,
        "signedSensitivity": signed,
        "adverse": adverse,
        "insurance": sum(value(record, "Insurance_Cost_USD") for record in records),
        "penalty": sum(value(record, "Penalty_Cost_USD") for record in records),
        "plannedDays": planned,
        "actualDays": actual,
        "delayDays": delay,
        "heldAgeDays": sum(value(record, "Delay_Days") for record in held),
        "difotHits": difot_hits,
        "difotDenominator": len(completed),
        "difot": ratio(difot_hits, len(completed)),
        "costPerTon": ratio(cost, tonnes) / 100 if tonnes else None,
        "revenuePerTon": ratio(contracted, tonnes) / 100 if tonnes else None,
        "insuranceBurden": ratio(sum(value(record, "Insurance_Cost_USD") for record in records), cargo_value),
        "delayAttribution": ratio(sum(value(record, "Penalty_Cost_USD") for record in records), cost),
        "transitIndex": ratio(actual, planned),
        "deliveredShipments": len(completed),
        "heldShipments": len(held),
    }


def clean_number(value_to_clean):
    if isinstance(value_to_clean, float) and not math.isfinite(value_to_clean):
        return None
    if isinstance(value_to_clean, dict):
        return {key: clean_number(value) for key, value in value_to_clean.items()}
    if isinstance(value_to_clean, list):
        return [clean_number(value) for value in value_to_clean]
    return value_to_clean


def group_records(records: list[dict], keys: tuple[str, ...]) -> dict[tuple, list[dict]]:
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for record in records:
        groups[tuple(record[key] for key in keys)].append(record)
    return groups


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def empirical_rank(values: list[float], current: float) -> float:
    if len(values) <= 1:
        return 50.0
    return sum(value <= current for value in values) / len(values) * 100


def service_interval(hits: int, sample: int) -> dict | None:
    if not sample:
        return None

    def beta_fraction(a: float, b: float, x: float) -> float:
        tiny = 3e-30
        qab, qap, qam = a + b, a + 1, a - 1
        c, d = 1.0, 1.0 - qab * x / qap
        d = max(abs(d), tiny) * (1 if d >= 0 else -1)
        d = 1 / d
        h = d
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

    # Jeffreys pseudo-counts keep 100% cells from presenting as certainty.
    alpha, beta = hits + 0.5, sample - hits + 0.5
    return {
        "adjusted": alpha / (alpha + beta) * 100,
        "lower": beta_quantile(0.05, alpha, beta) * 100,
        "upper": beta_quantile(0.95, alpha, beta) * 100,
    }


def robustness_lattice(rows: list[dict]) -> dict:
    vectors = [
        (m, insurance, delay, concentration)
        for m in range(35, 56, 5)
        for insurance in range(5, 21, 5)
        for delay in range(15, 31, 5)
        for concentration in range(15, 31, 5)
        if m + insurance + delay + concentration == 100
    ]
    raw_values = {
        component: [row[component] for row in rows]
        for component in ("M", "I", "D", "C")
    }
    result = []
    for row in rows:
        ranks = []
        for weights in vectors:
            scored = sorted(
                (
                    0.01 * sum(
                        weight * empirical_rank(raw_values[component], candidate[component])
                        for weight, component in zip(weights, ("M", "I", "D", "C"))
                    ),
                    candidate["name"],
                )
                for candidate in rows
            )
            ranks.append(next(index for index, (_, name) in enumerate(reversed(scored), 1) if name == row["name"]))
        result.append(
            {
                "name": row["name"],
                "minRank": min(ranks),
                "maxRank": max(ranks),
                "topTwoShare": sum(rank <= 2 for rank in ranks) / len(ranks) * 100,
            }
        )
    return {"vectors": len(vectors), "rows": result}


def flags_for(summary: dict, top_decile: float) -> list[str]:
    flags = []
    if summary["heldShipments"]:
        flags.append("HELD_OPEN_EXPOSURE")
    if summary["adverse"] >= top_decile and summary["adverse"] > 0:
        flags.append("TOP_DECILE_IMPACT")
    if summary["deliveredShipments"] and summary["grossMargin"] < 0:
        flags.append("DELIVERED_NEGATIVE_MARGIN")
    if summary["difot"] is not None and summary["difot"] < 90:
        flags.append("DIFOT_BREACH")
    if summary["shipments"] < 3:
        flags.append("LOW_SAMPLE")
    return flags


def score_rows(groups: dict[str, tuple[list[dict], dict, float]], top_deciles: dict[str, float]) -> list[dict]:
    prepared = []
    for name, (records, summary, concentration) in groups.items():
        prepared.append(
            {
                "name": name,
                "summary": summary,
                "M": summary["adverse"] / summary["contracted"] * 100 if summary["contracted"] else 0,
                "I": summary["insuranceBurden"] or 0,
                "D": summary["delayAttribution"] or 0,
                "C": concentration,
                "records": records,
            }
        )

    score_components = {}
    for component in ("M", "I", "D", "C"):
        raw = [item[component] for item in prepared]
        low = percentile(raw, 0.05)
        high = percentile(raw, 0.95)
        capped = [min(max(item[component], low), high) for item in prepared]
        score_components[component] = [empirical_rank(capped, value) for value in capped]

    for index, item in enumerate(prepared):
        item["score"] = round(
            0.45 * score_components["M"][index]
            + 0.15 * score_components["I"][index]
            + 0.20 * score_components["D"][index]
            + 0.20 * score_components["C"][index]
        )
        item["flags"] = flags_for(item["summary"], top_deciles[item["name"]])

    prepared.sort(key=lambda item: (-item["score"], -item["summary"]["adverse"], item["name"]))
    return [
        {
            "name": item["name"],
            "score": item["score"],
            "M": item["M"],
            "I": item["I"],
            "D": item["D"],
            "C": item["C"],
            "sample": item["summary"]["shipments"],
            "adverse": item["summary"]["adverse"],
            "contracted": item["summary"]["contracted"],
            "grossMargin": item["summary"]["grossMargin"],
            "difot": item["summary"]["difot"],
            "flags": item["flags"],
        }
        for item in prepared
    ]


def action_for_cell(cell: dict) -> tuple[str, str, str]:
    if cell["kind"] == "held":
        return (
            "Release / route validate",
            "COO",
            "HELD_OPEN_EXPOSURE or age >5 days",
        )
    if "DELIVERED_NEGATIVE_MARGIN" in cell["flags"] or (cell["severity"] or 0) > 100:
        return (
            "Reprice / matched-route pilot",
            "CCO",
            "Contribution-negative or severity >100%",
        )
    return ("Govern / monitor", "COO", "No hard trigger; recheck at next review")


def build_cells(shock_records: list[dict]) -> list[dict]:
    groups = group_records(shock_records, ("Customer_Name", "Product_Category", "routeLabel"))
    summaries = {key: aggregate(records) for key, records in groups.items()}
    adverse_values = [summary["adverse"] for summary in summaries.values()]
    top_decile = percentile(adverse_values, 0.9)
    cells = []
    for (customer, product, route), records in groups.items():
        summary = summaries[(customer, product, route)]
        kind = records[0]["kind"]
        flags = flags_for(summary, top_decile)
        cell = {
            "customer": customer,
            "product": product,
            "route": route,
            "kind": kind,
            "shipments": summary["shipments"],
            "tonnes": summary["tonnes"],
            "contracted": summary["contracted"],
            "recognized": summary["recognized"],
            "cost": summary["cost"],
            "grossMargin": summary["grossMargin"],
            "signedSensitivity": summary["signedSensitivity"],
            "adverse": summary["adverse"],
            "severity": summary["adverse"] / summary["contracted"] * 100 if kind == "delivered" and summary["contracted"] else None,
            "zeroMarginSurcharge": max(summary["cost"] - summary["recognized"], 0) if kind == "delivered" else None,
            "benchmarkPreservingSurcharge": max(summary["signedSensitivity"], 0) if kind == "delivered" else None,
            "insurance": summary["insurance"],
            "penalty": summary["penalty"],
            "insuranceBurden": summary["insuranceBurden"],
            "delayAttribution": summary["delayAttribution"],
            "difot": summary["difot"],
            "difotHits": summary["difotHits"],
            "difotDenominator": summary["difotDenominator"],
            "delayDays": summary["delayDays"],
            "delayPerShipment": summary["delayDays"] / summary["deliveredShipments"] if summary["deliveredShipments"] else None,
            "heldAgeDays": summary["heldAgeDays"] if kind == "held" else None,
            "heldRevenue": summary["contracted"] if kind == "held" else 0,
            "flags": flags,
        }
        cell["action"], cell["owner"], cell["trigger"] = action_for_cell(cell)
        cells.append(cell)
    return sorted(cells, key=lambda item: (-item["adverse"], item["customer"], item["product"], item["route"]))


def build_frontier(delivered_records: list[dict]) -> list[dict]:
    groups = group_records(delivered_records, ("Product_Category", "routeLabel"))
    by_product: dict[str, list[dict]] = defaultdict(list)
    for (product, route), records in groups.items():
        summary = aggregate(records)
        by_product[product].append(
            {
                "route": route,
                "costPerTon": summary["costPerTon"],
                "difot": summary["difot"],
                "sample": summary["shipments"],
                "interval": service_interval(summary["difotHits"], summary["difotDenominator"]),
            }
        )

    frontier = []
    for product, options in sorted(by_product.items()):
        best = None
        for candidate in options:
            dominates = [
                other
                for other in options
                if other["route"] != candidate["route"]
                and candidate["costPerTon"] <= other["costPerTon"]
                and candidate["difot"] >= other["difot"]
                and (candidate["costPerTon"] < other["costPerTon"] or candidate["difot"] > other["difot"])
            ]
            if dominates and (best is None or len(dominates) > len(best[1])):
                best = (candidate, dominates)
        if best:
            preferred, dominated = best
            compared = sorted(dominated, key=lambda item: (-item["costPerTon"], item["difot"]))[0]
            status = "matched pilot hypothesis"
        else:
            preferred = min(options, key=lambda item: item["costPerTon"])
            compared = next((item for item in options if item["route"] != preferred["route"]), None)
            status = "no observed dominance; validate feasibility"
        frontier.append(
            {
                "product": product,
                "preferred": preferred["route"],
                "compared": compared["route"] if compared else None,
                "preferredCostPerTon": preferred["costPerTon"],
                "comparedCostPerTon": compared["costPerTon"] if compared else None,
                "preferredDifot": preferred["difot"],
                "comparedDifot": compared["difot"] if compared else None,
                "preferredInterval": preferred["interval"],
                "comparedInterval": compared["interval"] if compared else None,
                "preferredSample": preferred["sample"],
                "comparedSample": compared["sample"] if compared else None,
                "status": status,
            }
        )
    return frontier


def concentration_metrics(records: list[dict], key: str, field: str) -> dict:
    totals: dict[str, float] = defaultdict(float)
    for record in records:
        totals[record[key]] += max(value(record, field), 0)
    total = sum(totals.values())
    shares = [amount / total for amount in totals.values()] if total else []
    hhi = sum(share * share for share in shares)
    return {"hhi": hhi, "effectiveNumber": 1 / hhi if hhi else None}


def route_is_feasible(record: dict, route_input: dict) -> bool:
    return record["Cargo_Type"] in route_input.get("cargoTypes", [])


def route_unit_economics(record: dict, route_input: dict, inputs: dict) -> dict:
    tonnes = max(value(record, "Cargo_Weight_Tons"), 1.0)
    revenue_per_ton = value(record, "Contracted_Freight_Revenue_USD") / tonnes
    recoverable_per_ton = max(float(route_input["recoverableSurchargePerTon"]), 0) * inputs["recoveryRate"]
    freight_per_ton = route_input["costPerTon"] * inputs["costMultiplier"]
    insurance_per_ton = (
        value(record, "Cargo_Value_USD")
        / tonnes
        * route_input["insuranceRate"]
        * inputs["insuranceMultiplier"]
    )
    future_penalty_per_ton = route_input["expectedFuturePenaltyPerTon"] * inputs["penaltyMultiplier"]
    service_bound = min(max(route_input["serviceLowerBound"] * inputs["serviceMultiplier"], 0), 1)
    failure_per_ton = route_input["failureCostPerTon"] * (1 - service_bound)
    return {
        "unitContribution": (
            revenue_per_ton
            + recoverable_per_ton
            - freight_per_ton
            - insurance_per_ton
            - future_penalty_per_ton
            - failure_per_ton
        ),
        "freight": freight_per_ton,
        "insurance": insurance_per_ton,
        "futurePenalty": future_penalty_per_ton,
        "failureCost": failure_per_ton,
        "recoverableSurcharge": recoverable_per_ton,
    }


def constrained_forward_ledger(held_records: list[dict], inputs: dict, route_inputs: dict) -> dict:
    """Allocate the open queue against explicit route inputs and conserve flow."""
    inflow_multiplier = max(inputs["heldInflowMultiplier"], 0)
    demand = [(record, 1.0, "opening") for record in held_records]
    demand.extend((record, inflow_multiplier, "inflow") for record in held_records)
    opening_tonnes = sum(value(record, "Cargo_Weight_Tons") for record in held_records)
    opening_revenue = sum(value(record, "Contracted_Freight_Revenue_USD") for record in held_records)
    inflow_tonnes = opening_tonnes * inflow_multiplier
    inflow_revenue = opening_revenue * inflow_multiplier
    queue_tonnes = opening_tonnes + inflow_tonnes
    queue_revenue = opening_revenue + inflow_revenue
    clear_target_tonnes = queue_tonnes * min(max(inputs["clearRate"], 0), 1)
    remaining_target = clear_target_tonnes
    capacities = {
        route: max(float(route_input.get("capacityTonnes") or 0), 0)
        for route, route_input in route_inputs.items()
    }
    available_capacity = sum(
        capacity
        for route, capacity in capacities.items()
        if route not in inputs["unavailableRoutes"]
    )
    allocations = {
        route: {
            "route": route,
            "allocatedTonnes": 0.0,
            "capacityTonnes": capacities[route],
            "clearedShipments": 0.0,
            "forwardContribution": 0.0,
            "serviceLowerBound": min(
                max(float(route_inputs[route]["serviceLowerBound"]) * inputs["serviceMultiplier"], 0),
                1,
            ),
        }
        for route in route_inputs
    }
    cleared_revenue = 0.0
    cleared_shipments = 0.0
    forward_contribution = 0.0
    forward_cost = 0.0
    recovered_surcharge = 0.0
    expected_failure_cost = 0.0

    demand.sort(
        key=lambda item: (
            -(value(item[0], "Penalty_Cost_USD") / max(value(item[0], "Delay_Days"), 1)),
            -value(item[0], "Contracted_Freight_Revenue_USD"),
            item[0]["Shipment_ID"],
            item[2],
        )
    )
    for record, scale, _source in demand:
        quantity = value(record, "Cargo_Weight_Tons") * scale
        if quantity <= 0 or remaining_target <= 0:
            continue
        while quantity > 1e-9 and remaining_target > 1e-9:
            options = [
                (route, route_input, route_unit_economics(record, route_input, inputs))
                for route, route_input in route_inputs.items()
                if route not in inputs["unavailableRoutes"]
                and capacities.get(route, 0) > 1e-9
                and route_is_feasible(record, route_input)
            ]
            if not options:
                break
            route, _route_input, economics = max(options, key=lambda item: item[2]["unitContribution"])
            amount = min(quantity, remaining_target, capacities[route])
            share_of_record = amount / max(value(record, "Cargo_Weight_Tons"), 1.0)
            allocation = allocations[route]
            allocation["allocatedTonnes"] += amount
            allocation["clearedShipments"] += share_of_record
            allocation["forwardContribution"] += amount * economics["unitContribution"]
            capacities[route] -= amount
            quantity -= amount
            remaining_target -= amount
            cleared_shipments += share_of_record
            cleared_revenue += value(record, "Contracted_Freight_Revenue_USD") * share_of_record
            contribution = amount * economics["unitContribution"]
            forward_contribution += contribution
            forward_cost += amount * (
                economics["freight"] + economics["insurance"] + economics["futurePenalty"]
            )
            recovered_surcharge += amount * economics["recoverableSurcharge"]
            expected_failure_cost += amount * economics["failureCost"]

    cleared_tonnes = sum(item["allocatedTonnes"] for item in allocations.values())
    ending_held_tonnes = queue_tonnes - cleared_tonnes
    ending_held_revenue = queue_revenue - cleared_revenue
    for allocation in allocations.values():
        allocation["remainingCapacityTonnes"] = allocation["capacityTonnes"] - allocation["allocatedTonnes"]
        allocation["share"] = allocation["allocatedTonnes"] / cleared_tonnes * 100 if cleared_tonnes else 0
    forward_difot = (
        sum(item["allocatedTonnes"] * item["serviceLowerBound"] for item in allocations.values())
        / cleared_tonnes
        * 100
        if cleared_tonnes
        else None
    )
    flow = {
        "beginningHeldTonnes": opening_tonnes,
        "inflowTonnes": inflow_tonnes,
        "clearedTonnes": cleared_tonnes,
        "cancelledTonnes": 0.0,
        "endingHeldTonnes": ending_held_tonnes,
        "differenceTonnes": opening_tonnes + inflow_tonnes - cleared_tonnes - ending_held_tonnes,
    }
    return {
        "beginningHeldRevenue": opening_revenue,
        "inflowRevenue": inflow_revenue,
        "clearedRevenue": cleared_revenue,
        "endingHeldRevenue": ending_held_revenue,
        "beginningHeldTonnes": opening_tonnes,
        "inflowTonnes": inflow_tonnes,
        "clearTargetTonnes": clear_target_tonnes,
        "clearedTonnes": cleared_tonnes,
        "endingHeldTonnes": ending_held_tonnes,
        "clearedShipments": cleared_shipments,
        "endingHeldShipments": len(held_records) * (1 + inflow_multiplier) - cleared_shipments,
        "unservedTonnes": ending_held_tonnes,
        "totalContribution": forward_contribution,
        "forwardContribution": forward_contribution,
        "forwardCost": forward_cost,
        "recoveredSurcharge": recovered_surcharge,
        "expectedFailureCost": expected_failure_cost,
        "difot": forward_difot,
        "availableRouteTonnes": available_capacity,
        "optionUtilization": cleared_tonnes / available_capacity * 100 if available_capacity else None,
        "referenceRevenueIncluded": 0.0,
        "flow": flow,
        "routeAllocation": list(allocations.values()),
        "capacityRemaining": capacities,
    }


def scenario_outputs(
    scenarios: list[dict],
    held_records: list[dict],
    source_gate: dict,
    forward_status: dict,
    forward_payload: dict,
) -> list[dict]:
    route_inputs = forward_payload.get("routes", {}) if forward_status["ready"] else {}
    decision_ready = source_gate["pass"] and forward_status["ready"]
    outputs = []
    for definition in scenarios:
        inputs = definition["inputs"]
        gate_reasons = []
        if not source_gate["pass"]:
            gate_reasons.append(f"{APPROVED_RAW_ROWS}-row source gate is unverified")
        if not forward_status["ready"]:
            gate_reasons.append("owner-supplied forward inputs are not approved")
        if not decision_ready:
            outputs.append(
                {
                    "name": definition["name"],
                    "tone": definition["tone"],
                    "detail": definition["detail"],
                    "inputs": inputs,
                    "decisionReady": False,
                    "outputs": {"locked": True},
                    "diagnostics": None,
                    "flow": None,
                    "decisionGate": gate_reasons,
                    "action": definition["action"],
                    "assumptionSource": "No approved forward inputs; scenario outputs withheld.",
                    "inputOwner": "Operations / Network Planning · Procurement · Commercial · Finance",
                }
            )
            continue

        ledger = constrained_forward_ledger(held_records, inputs, route_inputs)
        triggers = []
        if ledger["endingHeldRevenue"] > ledger["beginningHeldRevenue"] * 0.05:
            triggers.append("Ending Held revenue remains open")
        if ledger["endingHeldTonnes"] > 0:
            triggers.append("Backlog remains after constrained allocation")
        outputs.append(
            {
                "name": definition["name"],
                "tone": definition["tone"],
                "detail": definition["detail"],
                "inputs": inputs,
                "decisionReady": decision_ready,
                "outputs": {
                    "locked": False,
                    "totalContribution": ledger["totalContribution"],
                    "beginningHeldRevenue": ledger["beginningHeldRevenue"],
                    "inflowRevenue": ledger["inflowRevenue"],
                    "clearedRevenue": ledger["clearedRevenue"],
                    "endingHeldRevenue": ledger["endingHeldRevenue"],
                    "beginningHeldTonnes": ledger["beginningHeldTonnes"],
                    "inflowTonnes": ledger["inflowTonnes"],
                    "clearedTonnes": ledger["clearedTonnes"],
                    "endingHeldTonnes": ledger["endingHeldTonnes"],
                    "flowBalanced": abs(ledger["flow"]["differenceTonnes"]) < 0.01,
                    "routeAllocation": ledger["routeAllocation"],
                    "difot": ledger["difot"],
                    "triggerCrossings": triggers,
                },
                "diagnostics": ledger,
                "flow": ledger["flow"],
                "decisionGate": gate_reasons,
                "action": definition["action"],
                "assumptionSource": forward_payload.get("source", "approved forward inputs"),
                "inputOwner": "Operations / Network Planning · Procurement · Commercial · Finance",
            }
        )
    return outputs


def build_data(
    records: list[dict],
    source_info: dict,
    duplicate_info: dict,
    source_manifest: dict,
    forward_payload: dict,
) -> tuple[dict, dict]:
    for record in records:
        record["kind"] = classify(record)
        record["routeLabel"] = ROUTE_LABELS.get(record["Route_Type"], record["Route_Type"])

    canonical_rows = len(records)
    source_gate = source_gate_status(source_info, duplicate_info, canonical_rows, source_manifest)
    forward_status = forward_input_status(forward_payload)
    direct = [record for record in records if record["kind"] == "reference"]
    shock = [record for record in records if record["kind"] != "reference"]
    delivered = [record for record in records if record["kind"] == "delivered"]
    held = [record for record in records if record["kind"] == "held"]
    portfolio = aggregate(records)
    shock_summary = aggregate(shock)
    delivered_summary = aggregate(delivered)
    held_summary = aggregate(held)
    direct_summary = aggregate(direct)
    full_revenue = portfolio["contracted"]

    controls = {
        "rawRows": source_info["sourceRows"],
        "canonicalRows": canonical_rows,
        "statedRows": STATED_ROWS,
        "approvedRawRows": APPROVED_RAW_ROWS,
        "directRows": len(direct),
        "shockRows": len(shock),
        "deliveredRows": len(delivered),
        "heldRows": len(held),
        "contractedRevenue": full_revenue,
        "recognizedRevenue": portfolio["recognized"],
        "heldRevenue": held_summary["contracted"],
        "totalCost": portfolio["cost"],
        "grossMargin": portfolio["grossMargin"],
        "shockSignedSensitivity": shock_summary["signedSensitivity"],
        "signedSensitivity": shock_summary["signedSensitivity"],
        "adverseSensitivity": shock_summary["adverse"],
        "deliveredSignedSensitivity": delivered_summary["signedSensitivity"],
        "deliveredAdverseSensitivity": delivered_summary["adverse"],
        "deliveredMargin": delivered_summary["grossMargin"],
        "deliveredBenchmarkContribution": delivered_summary["recognized"] - (delivered_summary["cost"] - delivered_summary["signedSensitivity"]),
        "deliveredDirectEquivalentCost": delivered_summary["cost"] - delivered_summary["signedSensitivity"],
        "favourableOffset": abs(sum(min(value(record, "Route_Margin_Sensitivity_USD"), 0) for record in shock)),
        "heldCost": held_summary["cost"],
        "heldPenalty": held_summary["penalty"],
        "heldInsurance": held_summary["insurance"],
        "heldTonnes": held_summary["tonnes"],
        "deliveredTonnes": delivered_summary["tonnes"],
        "heldDays": held_summary["heldAgeDays"],
        "heldMedianDays": statistics.median([value(record, "Delay_Days") for record in held]),
        "heldP90Days": percentile([value(record, "Delay_Days") for record in held], 0.9),
        "heldMaxDays": max(value(record, "Delay_Days") for record in held),
        "directDIFOT": direct_summary["difot"],
        "directDIFOTHits": direct_summary["difotHits"],
        "postDIFOT": delivered_summary["difot"],
        "deliveredDIFOTHits": delivered_summary["difotHits"],
        "totalTonnes": portfolio["tonnes"],
        "deliveredCost": delivered_summary["cost"],
        "deliveredInsurance": delivered_summary["insurance"],
        "deliveredPenalty": delivered_summary["penalty"],
    }

    route_groups = group_records(records, ("routeLabel",))
    route_order = ["Direct / benchmark", "Cape of Good Hope", "Pipeline Bypass", "Overland Truck", "Air Bridge", "Held in Gulf"]
    route_rows = []
    route_summaries = {}
    for route in route_order:
        route_records = route_groups.get((route,), [])
        if not route_records:
            continue
        summary = aggregate(route_records)
        route_summaries[route] = summary
        kind = route_records[0]["kind"]
        route_rows.append(
            {
                "name": route,
                "kind": kind,
                "shipments": summary["shipments"],
                "tonnes": summary["tonnes"],
                "deliveredShipments": summary["deliveredShipments"],
                "difot": summary["difot"],
                "difotHits": summary["difotHits"],
                "difotInterval": service_interval(summary["difotHits"], summary["difotDenominator"]),
                "costPerTon": summary["costPerTon"],
                "contracted": summary["contracted"],
                "recognized": summary["recognized"],
                "cost": summary["cost"],
                "adverse": summary["adverse"] if kind == "delivered" else None,
                "signedSensitivity": summary["signedSensitivity"] if kind == "delivered" else None,
                "delayDays": summary["delayDays"] if kind == "delivered" else None,
                "delayPerShipment": summary["delayDays"] / summary["deliveredShipments"] if summary["deliveredShipments"] else None,
                "heldAgeDays": summary["heldAgeDays"] if kind == "held" else None,
                "heldRevenue": summary["contracted"] if kind == "held" else None,
                "heldCost": summary["cost"] if kind == "held" else None,
                "insuranceBurden": summary["insuranceBurden"],
                "plannedDays": summary["plannedDays"] if kind == "delivered" else None,
                "actualDays": summary["actualDays"] if kind == "delivered" else None,
            }
        )

    shock_customer_groups = group_records(shock, ("Customer_Name",))
    customer_full_groups = group_records(records, ("Customer_Name",))
    customer_shares = {
        name: aggregate(group)["contracted"] / full_revenue * 100
        for (name,), group in customer_full_groups.items()
    }

    def weighted_customer_share(group: list[dict], summary: dict) -> float:
        if not summary["contracted"]:
            return 0
        return sum(
            value(record, "Contracted_Freight_Revenue_USD") * customer_shares[record["Customer_Name"]]
            for record in group
        ) / summary["contracted"]

    customer_rows = []
    customer_summaries = {}
    for (name,), group in shock_customer_groups.items():
        summary = aggregate(group)
        full_summary = aggregate(customer_full_groups[(name,)])
        customer_summaries[name] = (group, summary)
        customer_rows.append(
            {
                "name": name,
                "fullShare": full_summary["contracted"] / full_revenue * 100,
                "contracted": full_summary["contracted"],
                "shockContracted": summary["contracted"],
                "shipments": summary["shipments"],
                "shockShipments": summary["shipments"],
                "deliveredShipments": summary["deliveredShipments"],
                "heldShipments": summary["heldShipments"],
                "deliveredMisses": summary["difotDenominator"] - summary["difotHits"],
                "adverse": summary["adverse"],
                "signedSensitivity": summary["signedSensitivity"],
                "severity": summary["adverse"] / summary["contracted"] * 100 if summary["contracted"] else None,
                "held": sum(value(record, "Contracted_Freight_Revenue_USD") for record in group if record["kind"] == "held"),
                "difot": summary["difot"],
                "grossMargin": summary["grossMargin"],
            }
        )
    customer_rows.sort(key=lambda item: (-item["adverse"], item["name"]))

    product_groups = group_records(shock, ("Product_Category",))
    product_rows = []
    product_summaries = {}
    for (name,), group in product_groups.items():
        summary = aggregate(group)
        product_summaries[name] = (group, summary)
        product_rows.append(
            {
                "name": name,
                "shipments": summary["shipments"],
                "contracted": summary["contracted"],
                "adverse": summary["adverse"],
                "signedSensitivity": summary["signedSensitivity"],
                "severity": summary["adverse"] / summary["contracted"] * 100 if summary["contracted"] else None,
                "difot": summary["difot"],
                "grossMargin": summary["grossMargin"],
            }
        )
    product_rows.sort(key=lambda item: (-item["adverse"], item["name"]))

    cells = build_cells(shock)
    cell_rows = cells

    customer_adverse = [item["adverse"] for item in customer_rows]
    customer_top_decile = percentile(customer_adverse, 0.9)
    product_adverse = [item["adverse"] for item in product_rows]
    product_top_decile = percentile(product_adverse, 0.9)
    route_score_groups = {
        row["name"]: (
            route_groups[(row["name"],)],
            route_summaries[row["name"]],
            weighted_customer_share(route_groups[(row["name"],)], route_summaries[row["name"]]),
        )
        for row in route_rows
        if row["kind"] != "reference"
    }
    customer_score_groups = {
        name: (customer_summaries[name][0], customer_summaries[name][1], customer_shares[name])
        for name in customer_summaries
    }
    product_score_groups = {
        name: (
            product_summaries[name][0],
            product_summaries[name][1],
            weighted_customer_share(product_summaries[name][0], product_summaries[name][1]),
        )
        for name in product_summaries
    }
    score_rows_output = {
        "Customer": score_rows(customer_score_groups, {name: customer_top_decile for name in customer_summaries}),
        "Route": score_rows(route_score_groups, {name: percentile([summary["adverse"] for _, summary, _ in route_score_groups.values()], 0.9) for name in route_score_groups}),
        "Product": score_rows(product_score_groups, {name: product_top_decile for name in product_summaries}),
    }
    score_robustness = {name: robustness_lattice(rows) for name, rows in score_rows_output.items()}
    frontier = build_frontier(delivered)
    concentration = {
        "customerRevenue": concentration_metrics(records, "Customer_Name", "Contracted_Freight_Revenue_USD"),
        "routeSensitivity": concentration_metrics(shock, "routeLabel", "Route_Margin_Sensitivity_USD"),
        "productSensitivity": concentration_metrics(shock, "Product_Category", "Route_Margin_Sensitivity_USD"),
    }

    held_queue = []
    for record in held:
        days = value(record, "Delay_Days")
        product = record["Product_Category"]
        cargo = record["Cargo_Type"]
        if product in {"High-Tech Components", "Pharmaceuticals"}:
            option = "Overland first / Air exception"
        elif cargo.startswith("Bulk"):
            option = "Cape / Pipeline validation"
        else:
            option = "Cape / Overland validation"
        held_queue.append(
            {
                "id": record["Shipment_ID"],
                "customer": record["Customer_Name"],
                "product": product,
                "days": days,
                "penalty": value(record, "Penalty_Cost_USD"),
                "penaltyPerDay": value(record, "Penalty_Cost_USD") / days if days else None,
                "revenue": value(record, "Contracted_Freight_Revenue_USD"),
                "cost": value(record, "Total_Cost_to_Serve_USD"),
                "option": option,
            }
        )
    held_queue.sort(key=lambda item: (-(item["penaltyPerDay"] or 0), -item["revenue"], item["id"]))

    scenarios = scenario_outputs(
        SCENARIO_DEFINITIONS,
        held,
        source_gate,
        forward_status,
        forward_payload,
    )
    metadata = {
        "sourceFile": source_info["sourceFile"],
        "sourceSheet": source_info["sheet"],
        "sourceRows": canonical_rows,
        "rawRows": source_info["sourceRows"],
        "canonicalRows": canonical_rows,
        "approvedRawRows": APPROVED_RAW_ROWS,
        "caseStatedRows": STATED_ROWS,
        "sourceSha256": source_info["sourceSha256"],
        "sourceGate": source_gate,
        "observationStart": min(record["Departure_Date"] for record in records),
        "observationEnd": max(record["Departure_Date"] for record in records),
        "asOf": max(record["Departure_Date"] for record in records),
        "provisional": not source_gate["pass"] or not forward_status["ready"],
        "duplicatePolicy": f"Validate {APPROVED_RAW_ROWS} approved source rows; collapse exact duplicate Shipment_ID rows once; fail on blank or conflicting IDs.",
    }

    ledgers = {
        "delivered": {
            "recognizedRevenue": delivered_summary["recognized"],
            "actualCost": delivered_summary["cost"],
            "signedSensitivity": delivered_summary["signedSensitivity"],
            "directEquivalentCost": delivered_summary["cost"] - delivered_summary["signedSensitivity"],
            "benchmarkContribution": delivered_summary["recognized"] - (delivered_summary["cost"] - delivered_summary["signedSensitivity"]),
            "observedContribution": delivered_summary["grossMargin"],
        },
        "held": {
            "contractedRevenue": held_summary["contracted"],
            "accruedCost": held_summary["cost"],
            "penalties": held_summary["penalty"],
            "insurance": held_summary["insurance"],
            "tonnes": held_summary["tonnes"],
            "daysStuck": held_summary["heldAgeDays"],
        },
    }

    dashboard = {
        "metadata": metadata,
        "controls": controls,
        "ledgers": ledgers,
        "forwardModel": {
            "version": FORWARD_CONTRACT_VERSION,
            "decisionReady": source_gate["pass"] and forward_status["ready"],
            "sourceStatus": source_gate["status"],
            "inputStatus": forward_status,
            "requiredInputs": forward_status["requiredFields"],
            "lockedOutputs": ["scenario contribution", "route allocation", "capacity/utilization", "scenario DIFOT"],
        },
        "routes": route_rows,
        "customers": customer_rows,
        "products": product_rows,
        "cells": cell_rows,
        "heldQueue": held_queue,
        "scoreRows": score_rows_output,
        "scoreRobustness": score_robustness,
        "frontier": frontier,
        "concentration": concentration,
        "scenarios": scenarios,
        "actions": [
            {
                "priority": "01",
                "type": "Protect / change / stop",
                "title": "Release the queue",
                "owner": "COO",
                "horizon": "0–30 days",
                "trigger": "Any Held shipment >5 days or Held revenue >5% of portfolio.",
                "release": "Held revenue <5%; approved routes sustain ≥95% DIFOT for two weekly reviews.",
            },
            {
                "priority": "02",
                "type": "Protect / change / stop",
                "title": "Reopen material account terms",
                "owner": "CCO",
                "horizon": "0–90 days",
                "trigger": "Cell sensitivity/revenue >25%, Held revenue >$1m, or contribution-negative cell.",
                "release": "Sensitivity/revenue <10% and DIFOT ≥95% for 30 days.",
            },
            {
                "priority": "03",
                "type": "Protect / change / stop",
                "title": "Gate the route premium",
                "owner": "CSCO",
                "horizon": "0–365 days",
                "trigger": "Recovered surcharge + avoided loss fails to cover current quoted premium.",
                "release": "Use lower-cost feasible mode once service/economic hurdle clears.",
            },
            {
                "priority": "04",
                "type": "Protect / change / stop",
                "title": "Re-insure by corridor",
                "owner": "CRO",
                "horizon": "31–90 days",
                "trigger": "Recorded burden >1.5% of cargo value or top-quartile insurance burden.",
                "release": "Burden <0.75% for 60 days with better premium + retained loss.",
            },
            {
                "priority": "05",
                "type": "Protect / change / stop",
                "title": "Stop unrecoverable offers",
                "owner": "CCO",
                "horizon": "31–365 days",
                "trigger": "Negative contribution persists after route, price, insurance and service redesign.",
                "release": "Re-enter only with positive prospective contribution and enforceable recovery.",
            },
        ],
    }

    checks = {
        "canonicalUniqueIds": len(records) == len({record["Shipment_ID"] for record in records}),
        "canonicalRows": len(records) == source_info["sourceRows"] - duplicate_info["duplicateExcessRows"],
        "portfolioSplit": len(direct) + len(shock) == len(records),
        "shockSplit": len(delivered) + len(held) == len(shock),
        "revenueReconciles": abs(portfolio["contracted"] - portfolio["recognized"] - held_summary["contracted"]) < 0.01,
        "marginReconciles": abs(portfolio["grossMargin"] - (portfolio["recognized"] - portfolio["cost"])) < 0.01,
        "deliveredMarginReconciles": abs(delivered_summary["grossMargin"] - (delivered_summary["recognized"] - delivered_summary["cost"])) < 0.01,
        "sensitivityReconciles": abs(shock_summary["signedSensitivity"] - delivered_summary["signedSensitivity"] - held_summary["signedSensitivity"]) < 0.01,
        "actionCellsAreComplete": len(cell_rows) == 44,
        "heldQueueIsComplete": len(held_queue) == len(held),
        "heldHasNoDeliveredDIFOT": all(cell["difot"] is None for cell in cell_rows if cell["kind"] == "held"),
        "directAdverseExcluded": all(row["adverse"] is None for row in route_rows if row["kind"] == "reference"),
        "serviceIntervalsValid": all(
            row["difotInterval"] is None
            or 0 <= row["difotInterval"]["lower"] <= row["difotInterval"]["adjusted"] <= row["difotInterval"]["upper"] <= 100
            for row in route_rows
        ),
        "weightLatticeComplete": all(item["vectors"] == 50 for item in score_robustness.values()),
        "frontierComplete": len(frontier) == len(product_summaries),
        "noConflicts": not duplicate_info["conflicts"],
        "noBlankShipmentIds": not duplicate_info["blankShipmentIdRows"],
        "scenarioLedgerShape": all(
            (
                not scenario["decisionReady"]
                and scenario["outputs"] == {"locked": True}
                and scenario["diagnostics"] is None
            )
            or (
                scenario["decisionReady"]
                and "totalContribution" in scenario["outputs"]
                and "routeAllocation" in scenario["outputs"]
                and "difot" in scenario["outputs"]
            )
            for scenario in scenarios
        ),
        "scenarioFlowConserves": all(
            not scenario["decisionReady"] or scenario["outputs"]["flowBalanced"]
            for scenario in scenarios
        ),
        "scenarioCapacityConserves": all(
            not scenario["decisionReady"]
            or all(
                allocation["allocatedTonnes"] <= allocation["capacityTonnes"] + 0.01
                for allocation in scenario["diagnostics"]["routeAllocation"]
            )
            for scenario in scenarios
        ),
        "scenarioNoReferenceRevenue": all(
            not scenario["decisionReady"]
            or scenario["diagnostics"]["referenceRevenueIncluded"] == 0
            for scenario in scenarios
        ),
    }
    qa = {
        "source": metadata,
        "sourceGate": source_gate,
        "forwardInputs": forward_status,
        "duplicateAdjudication": duplicate_info,
        "counts": {
            "sourceRows": canonical_rows,
            "rawRows": source_info["sourceRows"],
            "canonicalRows": len(records),
            "directRows": len(direct),
            "shockRows": len(shock),
            "deliveredRows": len(delivered),
            "heldRows": len(held),
            "actionCells": len(cell_rows),
        },
        "controls": {
            "contractedRevenue": portfolio["contracted"],
            "recognizedRevenue": portfolio["recognized"],
            "heldRevenue": held_summary["contracted"],
            "shockSignedSensitivity": shock_summary["signedSensitivity"],
            "shockAdverseSensitivity": shock_summary["adverse"],
            "postDeliveredDIFOT": delivered_summary["difot"],
        },
        "checks": checks,
        "analyticalChecksPass": all(checks.values()),
        "pass": all(checks.values()),
        "boardSafe": all(checks.values()) and source_gate["pass"] and forward_status["ready"],
    }
    return clean_number(dashboard), clean_number(qa)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workbook", type=Path, help="approved raw workbook; cleaned workbook is used only as a provisional fallback")
    parser.add_argument("--dashboard", type=Path, default=DASHBOARD_PATH)
    parser.add_argument("--qa", type=Path, default=QA_PATH)
    parser.add_argument("--source-manifest", type=Path, default=SOURCE_MANIFEST_PATH)
    parser.add_argument("--duplicate-adjudication", type=Path, default=DUPLICATE_ADJUDICATION_PATH)
    parser.add_argument("--forward-inputs", type=Path, default=FORWARD_INPUTS_PATH)
    parser.add_argument("--strict-source", action="store_true", help="fail unless the approved source contract is verified")
    parser.add_argument("--strict-board", action="store_true", help="fail unless source and owner-supplied forward contracts are verified")
    args = parser.parse_args()

    try:
        source_manifest = load_json(args.source_manifest)
        approved_source = ROOT / source_manifest.get("approvedRawSourceFile", "")
        workbook = args.workbook or (approved_source if approved_source.exists() else DEFAULT_WORKBOOK)
        raw_records, source_info = parse_workbook(workbook)
        records, duplicate_info = canonicalize(raw_records)
        forward_payload = load_json(args.forward_inputs)
        dashboard, qa = build_data(records, source_info, duplicate_info, source_manifest, forward_payload)
        write_json(args.dashboard, dashboard)
        write_json(args.qa, qa)
        write_json(
            args.duplicate_adjudication,
            {
                "source": source_info,
                "contract": {
                    "approvedRawRows": source_manifest.get("approvedRawRows", APPROVED_RAW_ROWS),
                    "expectedCanonicalRows": source_manifest.get("expectedCanonicalRows", EXPECTED_CANONICAL_ROWS),
                    "expectedDuplicateExcessRows": source_manifest.get("expectedDuplicateExcessRows", EXPECTED_DUPLICATE_EXCESS),
                },
                "duplicateAdjudication": duplicate_info,
                "sourceGate": qa["sourceGate"],
            },
        )
    except (KeyError, OSError, ET.ParseError, ValueError, BadZipFile) as error:
        print(f"analysis failed: {error}", file=sys.stderr)
        return 1

    failed = [name for name, passed in qa["checks"].items() if not passed]
    if duplicate_info["conflicts"]:
        failed.append("conflicting duplicate Shipment_ID")
    if duplicate_info["blankShipmentIdRows"]:
        failed.append("blank Shipment_ID")
    if failed:
        print(f"QA failed: {', '.join(failed)}", file=sys.stderr)
        return 1
    if (args.strict_source or args.strict_board) and not qa["sourceGate"]["pass"]:
        failed_gate = [name for name, passed in qa["sourceGate"]["checks"].items() if not passed]
        print(f"source gate failed: {', '.join(failed_gate)}", file=sys.stderr)
        return 1
    forward_status = qa["forwardInputs"]
    if args.strict_board and not forward_status["ready"]:
        failed_inputs = [
            name
            for name, passed in {
                "approved": forward_status["approved"],
                "complete": forward_status["complete"],
                "versioned": forward_status["versioned"],
                "source": forward_status["hasSource"],
                "effectiveDate": forward_status["hasEffectiveDate"],
            }.items()
            if not passed
        ]
        print(f"forward input gate failed: {', '.join(failed_inputs)}", file=sys.stderr)
        return 1
    print(
        f"Generated {args.dashboard} and {args.qa}: "
        f"{qa['counts']['canonicalRows']} canonical rows, "
        f"{qa['counts']['actionCells']} action cells, "
        f"{qa['counts']['heldRows']} Held rows."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
