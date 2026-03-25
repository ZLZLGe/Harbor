#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
import re
from collections import defaultdict
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET


INPUT_PATH = Path("/root/commission_settlement_pack.xlsm")
OUTPUT_PATH = Path("/root/commission_exceptions.json")

NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pkg": "http://schemas.openxmlformats.org/package/2006/relationships",
}


def column_index(cell_ref: str) -> int:
    letters = "".join(ch for ch in cell_ref if ch.isalpha())
    value = 0
    for ch in letters:
        value = value * 26 + ord(ch.upper()) - 64
    return value - 1


def parse_cell(cell):
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        parts = [node.text or "" for node in cell.findall(".//main:t", NS)]
        return "".join(parts)
    value = cell.find("main:v", NS)
    if value is None or value.text is None:
        return None
    text = value.text.strip()
    if re.fullmatch(r"-?\d+", text):
        return int(text)
    try:
        return float(text)
    except ValueError:
        return text


def read_workbook(path: Path):
    with ZipFile(path) as zf:
        workbook = ET.fromstring(zf.read("xl/workbook.xml"))
        rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        rel_map = {
            rel.attrib["Id"]: rel.attrib["Target"]
            for rel in rels.findall("pkg:Relationship", NS)
        }
        result = {}
        for sheet in workbook.findall("main:sheets/main:sheet", NS):
            name = sheet.attrib["name"]
            target = rel_map[sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]]
            sheet_xml = ET.fromstring(zf.read(f"xl/{target}"))
            rows = []
            for row in sheet_xml.findall("main:sheetData/main:row", NS):
                values = {}
                for cell in row.findall("main:c", NS):
                    values[column_index(cell.attrib.get("r", "A1"))] = parse_cell(cell)
                max_index = max(values, default=-1)
                rows.append([values.get(idx) for idx in range(max_index + 1)])
            result[name] = rows
        return result


def sheet_to_dicts(rows):
    header = rows[0]
    records = []
    for row in rows[1:]:
        padded = row + [None] * (len(header) - len(row))
        record = {header[idx]: padded[idx] for idx in range(len(header))}
        if any(value is not None for value in record.values()):
            records.append(record)
    return records


def pick_rule(rules, plan_code, region_code, monthly_sales):
    for rule in rules[(plan_code, region_code)]:
        maximum = rule["max_monthly_sales"]
        if monthly_sales >= rule["min_monthly_sales"] and (maximum is None or monthly_sales <= maximum):
            return rule
    raise ValueError(f"missing rule for {plan_code} {region_code} {monthly_sales}")


def fmt_money(value):
    return f"{value:.2f}"


def fmt_rate(value):
    return f"{value:.3f}"


workbook = read_workbook(INPUT_PATH)
orders = sheet_to_dicts(workbook["Orders"])
reps = {row["rep_id"]: row for row in sheet_to_dicts(workbook["Rep Directory"])}
advances = {
    (row["payout_month"], row["rep_id"]): float(row["advance_amount"])
    for row in sheet_to_dicts(workbook["Advance Ledger"])
}

rules = defaultdict(list)
for row in sheet_to_dicts(workbook["Commission Rules"]):
    row["min_monthly_sales"] = float(row["min_monthly_sales"])
    row["max_monthly_sales"] = None if row["max_monthly_sales"] is None else float(row["max_monthly_sales"])
    row["commission_rate"] = float(row["commission_rate"])
    row["order_cap_amount"] = float(row["order_cap_amount"])
    rules[(row["plan_code"], row["region_code"])].append(row)

orders_by_id = {row["order_id"]: row for row in orders}
monthly_sales = defaultdict(float)
for row in orders:
    monthly_sales[(row["payout_month"], row["rep_id"])] += float(row["net_bookings"])

manual_rows = sheet_to_dicts(workbook["Manual Settlements"])
first_seen = {}
monthly_gross = defaultdict(float)
monthly_net = defaultdict(float)
exceptions = []

for row in manual_rows:
    payout_month = row["payout_month"]
    rep_id = row["rep_id"]
    rep = reps[rep_id]
    rep_name = rep["rep_name"]
    order = orders_by_id[row["order_id"]]
    gross = float(row["gross_commission"])
    rate_used = float(row["rate_used"])
    order_key = (payout_month, rep_id, row["order_id"])
    current_monthly_sales = monthly_sales[(payout_month, rep_id)]
    correct_rule = pick_rule(rules, rep["plan_code"], order["market_region"], current_monthly_sales)

    monthly_gross[(payout_month, rep_id)] += gross
    monthly_net[(payout_month, rep_id)] += float(row["net_payout"])

    if order_key in first_seen:
        exceptions.append(
            {
                "exception_type": "Duplicate Credit",
                "payout_month": payout_month,
                "rep_id": rep_id,
                "rep_name": rep_name,
                "order_id": row["order_id"],
                "settlement_id": row["settlement_id"],
                "expected_value": f"Single settlement row for {rep_id} / {row['order_id']} / {payout_month}",
                "actual_value": f"Duplicate of {first_seen[order_key]}",
                "impact_amount": round(gross, 2),
            }
        )
    else:
        first_seen[order_key] = row["settlement_id"]

    if row["rule_region_used"] != order["market_region"]:
        exceptions.append(
            {
                "exception_type": "Region Rule Mismatch",
                "payout_month": payout_month,
                "rep_id": rep_id,
                "rep_name": rep_name,
                "order_id": row["order_id"],
                "settlement_id": row["settlement_id"],
                "expected_value": order["market_region"],
                "actual_value": row["rule_region_used"],
                "impact_amount": 0.00,
            }
        )

    if row["tier_used"] != correct_rule["tier_name"] or abs(rate_used - correct_rule["commission_rate"]) > 0.00001:
        expected_commission = float(order["net_bookings"]) * correct_rule["commission_rate"]
        exceptions.append(
            {
                "exception_type": "Wrong Tier",
                "payout_month": payout_month,
                "rep_id": rep_id,
                "rep_name": rep_name,
                "order_id": row["order_id"],
                "settlement_id": row["settlement_id"],
                "expected_value": f"Tier {correct_rule['tier_name']} @ {fmt_rate(correct_rule['commission_rate'])}",
                "actual_value": f"Tier {row['tier_used']} @ {fmt_rate(rate_used)}",
                "impact_amount": round(abs(gross - expected_commission), 2),
            }
        )

    if gross - correct_rule["order_cap_amount"] > 0.01:
        exceptions.append(
            {
                "exception_type": "Cap Failure",
                "payout_month": payout_month,
                "rep_id": rep_id,
                "rep_name": rep_name,
                "order_id": row["order_id"],
                "settlement_id": row["settlement_id"],
                "expected_value": f"Cap {fmt_money(correct_rule['order_cap_amount'])}",
                "actual_value": f"Gross {fmt_money(gross)}",
                "impact_amount": round(gross - correct_rule["order_cap_amount"], 2),
            }
        )

for payout_month, rep_id in sorted(monthly_gross):
    rep = reps[rep_id]
    expected_net = monthly_gross[(payout_month, rep_id)] - advances.get((payout_month, rep_id), 0.0)
    actual_net = monthly_net[(payout_month, rep_id)]
    if abs(actual_net - expected_net) > 0.01:
        exceptions.append(
            {
                "exception_type": "Net Inconsistency",
                "payout_month": payout_month,
                "rep_id": rep_id,
                "rep_name": rep["rep_name"],
                "order_id": None,
                "settlement_id": None,
                "expected_value": f"Monthly net payout {fmt_money(expected_net)}",
                "actual_value": f"Monthly net payout {fmt_money(actual_net)}",
                "impact_amount": round(abs(actual_net - expected_net), 2),
            }
        )

def sort_key(item):
    return (
        item["payout_month"],
        item["rep_id"],
        item["order_id"] is None,
        item["order_id"] or "",
        item["exception_type"],
        item["settlement_id"] is None,
        item["settlement_id"] or "",
    )


exceptions.sort(key=sort_key)
OUTPUT_PATH.write_text(json.dumps(exceptions, indent=2), encoding="utf-8")
PY
