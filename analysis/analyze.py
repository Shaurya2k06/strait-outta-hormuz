#!/usr/bin/env python3
"""Build the dashboard data from the supplied workbook.

The workbook is parsed with the standard library so refreshes do not depend on
an analysis package being installed.  The script writes the UI data and a QA
report, and exits non-zero when a reconciliation check fails.
"""

from __future__ import annotations

import argparse
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
STATED_ROWS = 243

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

    return parsed, {"sheet": "Shipment_Data", "columns": headers, "sourceRows": len(parsed)}


def normalized_record(record: dict) -> tuple:
    return tuple(
        (key, round(value, 9) if isinstance(value, float) else value)
        for key, value in sorted(record.items())
    )


def canonicalize(records: list[dict]) -> tuple[list[dict], dict]:
    by_id: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        by_id[record["Shipment_ID"]].append(record)

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

    return canonical, {
        "duplicateGroups": len(exact_duplicates) + len(conflicts),
        "exactDuplicatesCollapsed": exact_duplicates,
        "conflicts": conflicts,
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


def scenario_outputs(scenarios: list[dict], controls: dict, route_rows: list[dict], cells: list[dict]) -> list[dict]:
    delivered_revenue = controls["recognizedRevenue"]
    delivered_adverse = controls["deliveredAdverseSensitivity"]
    delivered_base_cost = controls["deliveredCost"] - controls["deliveredInsurance"] - controls["deliveredPenalty"]
    held_tonnes = controls["heldTonnes"]
    available_route_tonnes = {row["name"]: row["tonnes"] for row in route_rows if row["kind"] == "delivered"}
    outputs = []
    for definition in scenarios:
        inputs = definition["inputs"]
        cost = delivered_base_cost * inputs["costMultiplier"]
        insurance = controls["deliveredInsurance"] * inputs["insuranceMultiplier"]
        penalty = controls["deliveredPenalty"] * inputs["penaltyMultiplier"]
        delivered_cost = cost + insurance + penalty
        recovered_surcharge = delivered_adverse * inputs["recoveryRate"]
        delivered_contribution = delivered_revenue + recovered_surcharge - delivered_cost
        projected_held_revenue = controls["heldRevenue"] * (1 - inputs["clearRate"]) * inputs["heldInflowMultiplier"]
        projected_held_cost = controls["heldCost"] * inputs["costMultiplier"]
        held_recovery = projected_held_revenue * inputs["recoveryRate"]
        total_contribution = delivered_contribution + held_recovery - projected_held_cost
        unserved_tonnes = held_tonnes * (1 - inputs["clearRate"]) * inputs["heldInflowMultiplier"]
        difot = min(100, max(0, (controls["postDIFOT"] or 0) * inputs["serviceMultiplier"]))

        available = [
            {"route": route, "tonnes": tonnes}
            for route, tonnes in available_route_tonnes.items()
            if route not in inputs["unavailableRoutes"]
        ]
        available_total = sum(item["tonnes"] for item in available)
        allocation = [
            {
                "route": item["route"],
                "tonnes": item["tonnes"],
                "share": item["tonnes"] / available_total * 100 if available_total else 0,
            }
            for item in available
        ]
        triggers = []
        if projected_held_revenue > controls["contractedRevenue"] * 0.05:
            triggers.append("Held revenue >5% of portfolio")
        if difot < 90:
            triggers.append("DIFOT <90%")
        if total_contribution < 0:
            triggers.append("Prospective contribution negative")
        if unserved_tonnes > controls["totalTonnes"] * 0.10:
            triggers.append("Unserved tonnes >10% of portfolio")

        cell_triggers = []
        for cell in cells:
            if cell["kind"] == "held":
                projected_cell_held = cell["heldRevenue"] * (1 - inputs["clearRate"]) * inputs["heldInflowMultiplier"]
                if projected_cell_held > controls["contractedRevenue"] * 0.01:
                    cell_triggers.append(f"{cell['customer']} × {cell['product']} × Held: open revenue trigger")
                continue
            cell_base_cost = cell["cost"] - cell["insurance"] - cell["penalty"]
            cell_cost = cell_base_cost * inputs["costMultiplier"] + cell["insurance"] * inputs["insuranceMultiplier"] + cell["penalty"] * inputs["penaltyMultiplier"]
            cell_contribution = cell["recognized"] + cell["adverse"] * inputs["recoveryRate"] - cell_cost
            if cell_contribution < 0:
                cell_triggers.append(f"{cell['customer']} × {cell['product']} × {cell['route']}: negative contribution")
        cell_triggers = cell_triggers[:6]

        outputs.append(
            {
                "name": definition["name"],
                "tone": definition["tone"],
                "detail": definition["detail"],
                "inputs": inputs,
                "outputs": {
                    "totalContribution": total_contribution,
                    "deliveredContribution": delivered_contribution,
                    "heldRevenue": projected_held_revenue,
                    "unservedTonnes": unserved_tonnes,
                    "difot": difot,
                    "recoveredSurcharge": recovered_surcharge,
                    "optionUtilization": available_total / controls["deliveredTonnes"] * 100 if controls["deliveredTonnes"] else 0,
                    "triggerCrossings": triggers,
                    "cellTriggerCrossings": cell_triggers,
                    "routeAllocation": allocation,
                },
                "action": definition["action"],
                "assumptionSource": "Proposal inputs; replace with owner-sourced live quotes, capacity and recovery terms.",
                "inputOwner": "Operations / Network Planning · Procurement · Commercial · Finance",
            }
        )
    return outputs


def build_data(records: list[dict], source_info: dict, duplicate_info: dict) -> tuple[dict, dict]:
    for record in records:
        record["kind"] = classify(record)
        record["routeLabel"] = ROUTE_LABELS.get(record["Route_Type"], record["Route_Type"])

    canonical_rows = len(records)
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
        "canonicalRows": canonical_rows,
        "statedRows": STATED_ROWS,
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

    scenarios = scenario_outputs(SCENARIO_DEFINITIONS, controls, route_rows, cell_rows)
    metadata = {
        "sourceFile": "R2-WAR ROOM MASTERPLAN-cleaned.xlsx",
        "sourceSheet": source_info["sheet"],
        "sourceRows": source_info["sourceRows"],
        "caseStatedRows": STATED_ROWS,
        "observationStart": min(record["Departure_Date"] for record in records),
        "observationEnd": max(record["Departure_Date"] for record in records),
        "asOf": max(record["Departure_Date"] for record in records),
        "provisional": source_info["sourceRows"] != STATED_ROWS,
        "duplicatePolicy": "Collapse exact duplicate Shipment_ID rows once; fail on conflicting fields.",
    }

    dashboard = {
        "metadata": metadata,
        "controls": controls,
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
        "canonicalRows": len(records) == source_info["sourceRows"] - len(duplicate_info["exactDuplicatesCollapsed"]),
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
    }
    qa = {
        "source": metadata,
        "duplicateAdjudication": duplicate_info,
        "counts": {
            "sourceRows": source_info["sourceRows"],
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
        "pass": all(checks.values()),
    }
    return clean_number(dashboard), clean_number(qa)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workbook", type=Path, default=DEFAULT_WORKBOOK)
    parser.add_argument("--dashboard", type=Path, default=DASHBOARD_PATH)
    parser.add_argument("--qa", type=Path, default=QA_PATH)
    parser.add_argument("--strict-source", action="store_true", help="fail unless the workbook has the case-stated 243 rows")
    args = parser.parse_args()

    try:
        raw_records, source_info = parse_workbook(args.workbook)
        records, duplicate_info = canonicalize(raw_records)
        dashboard, qa = build_data(records, source_info, duplicate_info)
        write_json(args.dashboard, dashboard)
        write_json(args.qa, qa)
    except (KeyError, OSError, ET.ParseError, ValueError, BadZipFile) as error:
        print(f"analysis failed: {error}", file=sys.stderr)
        return 1

    failed = [name for name, passed in qa["checks"].items() if not passed]
    if duplicate_info["conflicts"]:
        failed.append("conflicting duplicate Shipment_ID")
    if failed:
        print(f"QA failed: {', '.join(failed)}", file=sys.stderr)
        return 1
    if args.strict_source and qa["counts"]["canonicalRows"] != STATED_ROWS:
        print(f"source gate failed: expected {STATED_ROWS} canonical rows, found {qa['counts']['canonicalRows']}", file=sys.stderr)
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
