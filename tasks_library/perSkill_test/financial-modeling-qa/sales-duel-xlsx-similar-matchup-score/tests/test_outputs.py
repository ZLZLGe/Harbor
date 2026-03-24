import os
import re
import xml.etree.ElementTree as ET
from zipfile import ZipFile


WORKBOOK_PATH = "/root/campaign_showdown.xlsx"
OUTPUT_PATH = "/root/campaign_margin.txt"
EXPECTED_MARGIN = 2

NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pkg": "http://schemas.openxmlformats.org/package/2006/relationships",
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
            col_num = column_number(match.group(1))
            cell_type = cell.attrib.get("t")
            if cell_type == "inlineStr":
                value = "".join(node.text or "" for node in cell.findall(".//main:t", NS))
            else:
                value = parse_scalar(cell.findtext("main:v", default="", namespaces=NS))
            data[(row_number, col_num)] = value
    return data


def load_workbook_parts():
    with ZipFile(WORKBOOK_PATH) as zf:
        workbook = ET.fromstring(zf.read("xl/workbook.xml"))
        rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        target_by_id = {
            rel.attrib["Id"]: rel.attrib["Target"]
            for rel in rels.findall("pkg:Relationship", NS)
        }
        sheets = {}
        for sheet in workbook.find("main:sheets", NS):
            rel_id = sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
            target = "xl/" + target_by_id[rel_id]
            sheets[sheet.attrib["name"]] = parse_sheet(zf.read(target))
        sales_arena_xml = zf.read("xl/worksheets/sheet4.xml")
    return sheets, sales_arena_xml


def compute_margin() -> int:
    sheets, _ = load_workbook_parts()
    rule_cells = sheets["Scoring Rules"]
    arena_cells = sheets["Sales Arena"]

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

    header_row = None
    for row in range(1, 200):
        if arena_cells.get((row, 2)) == "CURRENT MATCHUP BOARD":
            header_row = row + 1
            break
    assert header_row is not None

    campaigns = []
    row = header_row + 1
    while True:
        campaign = arena_cells.get((row, 2))
        if not campaign or campaign == "END CURRENT BOARD":
            break
        campaigns.append(
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

    corrections = {}
    row = header_row + 1
    while True:
        campaign = arena_cells.get((row, 14))
        if not isinstance(campaign, str) or not campaign.startswith("CMP-"):
            break
        corrections[campaign] = (
            float(arena_cells[(row, 15)]),
            float(arena_cells[(row, 16)]),
            float(arena_cells[(row, 17)]),
        )
        row += 1

    def volume_bonus_for(deals: int) -> float:
        for min_deals, bonus in volume_ladder:
            if deals >= min_deals:
                return bonus
        return 0.0

    scores = {}
    for item in campaigns:
        revenue_delta, strategic_delta, discount_delta = corrections.get(
            item["campaign"], (0.0, 0.0, 0.0)
        )
        adjusted_revenue = item["revenue_k"] + revenue_delta
        adjusted_strategic = item["strategic_bonus"] + strategic_delta
        adjusted_discount = item["discount_pct"] + discount_delta

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
        score = round(
            base_score
            + efficiency_bonus
            + region_bonus[item["region"]]
            + volume_bonus_for(item["deals"])
            - discount_penalty,
            2,
        )
        scores[int(item["campaign"].split("-")[1])] = score

    margin = 0
    for odd_number in range(1, max(scores) + 1, 2):
        even_number = odd_number + 1
        if scores[odd_number] > scores[even_number]:
            margin += 1
        elif scores[even_number] > scores[odd_number]:
            margin -= 1
    return margin


class TestOutputs:
    def test_inputs_exist(self):
        assert os.path.exists(WORKBOOK_PATH), f"Missing input workbook: {WORKBOOK_PATH}"

    def test_hidden_adjustment_block_exists(self):
        _, sales_arena_xml = load_workbook_parts()
        xml_text = sales_arena_xml.decode("utf-8")
        assert 'min="14" max="17"' in xml_text
        assert 'hidden="1"' in xml_text

    def test_expected_margin_from_workbook(self):
        assert compute_margin() == EXPECTED_MARGIN

    def test_output_exists(self):
        assert os.path.exists(OUTPUT_PATH), f"Missing output file: {OUTPUT_PATH}"

    def test_output_format(self):
        with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
            content = f.read().strip()
        assert re.fullmatch(r"-?\d+", content), (
            f"campaign_margin.txt must contain only an integer, got {content!r}"
        )

    def test_output_matches_workbook_answer(self):
        with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
            content = f.read().strip()
        assert int(content) == compute_margin()
