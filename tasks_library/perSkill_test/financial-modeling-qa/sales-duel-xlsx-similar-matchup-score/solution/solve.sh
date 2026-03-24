#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import re
import xml.etree.ElementTree as ET
from zipfile import ZipFile

WORKBOOK_PATH = "/root/campaign_showdown.xlsx"
OUTPUT_PATH = "/root/campaign_margin.txt"

NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


def column_number(col_ref: str) -> int:
    value = 0
    for ch in col_ref:
        value = value * 26 + ord(ch) - 64
    return value


def parse_scalar(raw: str):
    if raw == "":
        return ""
    if re.fullmatch(r"-?\d+", raw):
        return int(raw)
    return float(raw)


def parse_sheet(xml_bytes: bytes) -> dict[tuple[int, int], object]:
    root = ET.fromstring(xml_bytes)
    data: dict[tuple[int, int], object] = {}
    sheet_data = root.find("main:sheetData", NS)
    if sheet_data is None:
        return data

    for row in sheet_data.findall("main:row", NS):
        for cell in row.findall("main:c", NS):
            ref = cell.attrib["r"]
            match = re.fullmatch(r"([A-Z]+)(\d+)", ref)
            if match is None:
                continue

            row_number = int(match.group(2))
            col_number = column_number(match.group(1))
            cell_type = cell.attrib.get("t")
            if cell_type == "inlineStr":
                text = "".join(node.text or "" for node in cell.findall(".//main:t", NS))
                data[(row_number, col_number)] = text
                continue

            raw = cell.findtext("main:v", default="", namespaces=NS)
            data[(row_number, col_number)] = parse_scalar(raw)

    return data


def load_sheets() -> dict[str, dict[tuple[int, int], object]]:
    with ZipFile(WORKBOOK_PATH) as zf:
        workbook = ET.fromstring(zf.read("xl/workbook.xml"))
        rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        target_by_id = {
            rel.attrib["Id"]: rel.attrib["Target"]
            for rel in rels.findall("{http://schemas.openxmlformats.org/package/2006/relationships}Relationship")
        }

        sheets = {}
        for sheet in workbook.find("main:sheets", NS):
            rel_id = sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
            target = "xl/" + target_by_id[rel_id]
            sheets[sheet.attrib["name"]] = parse_sheet(zf.read(target))
        return sheets


def load_rules(rule_cells: dict[tuple[int, int], object]):
    constants = {}
    row = 4
    while (row, 2) in rule_cells and (row, 3) in rule_cells:
        constants[str(rule_cells[(row, 2)])] = float(rule_cells[(row, 3)])
        row += 1

    region_bonus = {}
    row = 4
    while (row, 5) in rule_cells and (row, 6) in rule_cells:
        region_bonus[str(rule_cells[(row, 5)])] = float(rule_cells[(row, 6)])
        row += 1

    volume_ladder = []
    row = 4
    while (row, 8) in rule_cells and (row, 9) in rule_cells:
        volume_ladder.append((int(rule_cells[(row, 8)]), float(rule_cells[(row, 9)])))
        row += 1

    return constants, region_bonus, volume_ladder


def find_current_block(arena_cells: dict[tuple[int, int], object]) -> int:
    for row in range(1, 200):
        if arena_cells.get((row, 2)) == "CURRENT MATCHUP BOARD":
            return row + 1
    raise RuntimeError("Could not locate current campaign board.")


def load_campaigns(arena_cells: dict[tuple[int, int], object], header_row: int):
    rows = []
    row = header_row + 1
    while True:
        campaign = arena_cells.get((row, 2))
        if not campaign or campaign == "END CURRENT BOARD":
            break
        rows.append(
            {
                "campaign": str(campaign),
                "region": str(arena_cells[(row, 3)]),
                "leads": int(arena_cells[(row, 4)]),
                "meetings": int(arena_cells[(row, 5)]),
                "deals": int(arena_cells[(row, 6)]),
                "revenue_k": float(arena_cells[(row, 7)]),
                "discount_pct": float(arena_cells[(row, 8)]),
                "strategic_bonus": float(arena_cells[(row, 9)]),
            }
        )
        row += 1
    return rows


def load_corrections(arena_cells: dict[tuple[int, int], object], header_row: int):
    corrections = {}
    row = header_row + 1
    while True:
        campaign = arena_cells.get((row, 14))
        if not isinstance(campaign, str) or not campaign.startswith("CMP-"):
            break
        corrections[campaign] = {
            "revenue_delta_k": float(arena_cells[(row, 15)]),
            "strategic_delta": float(arena_cells[(row, 16)]),
            "discount_delta_pct": float(arena_cells[(row, 17)]),
        }
        row += 1
    return corrections


def volume_bonus(volume_ladder, deals: int) -> float:
    for min_deals, bonus in volume_ladder:
        if deals >= min_deals:
            return bonus
    return 0.0


def campaign_number(campaign: str) -> int:
    return int(campaign.split("-")[1])


def campaign_score(item, constants, region_bonus, volume_ladder, corrections) -> float:
    correction = corrections.get(item["campaign"], {})
    adjusted_revenue = item["revenue_k"] + correction.get("revenue_delta_k", 0.0)
    adjusted_strategic = item["strategic_bonus"] + correction.get("strategic_delta", 0.0)
    adjusted_discount = item["discount_pct"] + correction.get("discount_delta_pct", 0.0)

    base_score = (
        item["leads"] * constants["lead_weight"]
        + item["meetings"] * constants["meeting_weight"]
        + item["deals"] * constants["deal_weight"]
        + adjusted_revenue * constants["revenue_weight"]
        + adjusted_strategic
    )
    efficiency_bonus = (
        constants["efficiency_bonus"]
        if item["meetings"] / item["leads"] >= constants["efficiency_threshold"]
        else 0.0
    )
    discount_penalty = max(
        0.0, adjusted_discount - constants["discount_threshold"]
    ) * 100 * constants["penalty_per_pct_point"]

    return round(
        base_score
        + efficiency_bonus
        + region_bonus[item["region"]]
        + volume_bonus(volume_ladder, item["deals"])
        - discount_penalty,
        2,
    )


sheets = load_sheets()
constants, region_bonus, volume_ladder = load_rules(sheets["Scoring Rules"])
header_row = find_current_block(sheets["Sales Arena"])
campaigns = load_campaigns(sheets["Sales Arena"], header_row)
corrections = load_corrections(sheets["Sales Arena"], header_row)

scores = {
    campaign_number(item["campaign"]): campaign_score(
        item, constants, region_bonus, volume_ladder, corrections
    )
    for item in campaigns
}

margin = 0
for odd_number in range(1, max(scores) + 1, 2):
    even_number = odd_number + 1
    odd_score = scores[odd_number]
    even_score = scores[even_number]
    if odd_score > even_score:
        margin += 1
    elif even_score > odd_score:
        margin -= 1

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    f.write(str(margin))
PY
