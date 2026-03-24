import csv
import os
import re
import xml.etree.ElementTree as ET
from zipfile import ZipFile


WORKBOOK_PATH = "/root/draft_board_workbook.xlsx"
OUTPUT_PATH = "/root/draft_board.csv"

NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "pkg": "http://schemas.openxmlformats.org/package/2006/relationships",
}

EXPECTED_HEADER = [
    "rank",
    "prospect_id",
    "name",
    "position",
    "school",
    "injury_band",
    "composite_score",
]


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


def load_workbook(path: str) -> tuple[list[str], dict[str, dict[tuple[int, int], object]]]:
    with ZipFile(path) as zf:
        workbook = ET.fromstring(zf.read("xl/workbook.xml"))
        rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        target_by_id = {
            rel.attrib["Id"]: rel.attrib["Target"]
            for rel in rels.findall("pkg:Relationship", NS)
        }

        sheet_names = []
        sheets = {}
        for sheet in workbook.find("main:sheets", NS):
            sheet_names.append(sheet.attrib["name"])
            rel_id = sheet.attrib[
                "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
            ]
            target = "xl/" + target_by_id[rel_id]
            sheets[sheet.attrib["name"]] = parse_sheet(zf.read(target))
    return sheet_names, sheets


def row_values(cells: dict[tuple[int, int], object], row_number: int) -> list[object]:
    cols = sorted(col for current_row, col in cells if current_row == row_number)
    return [cells[(row_number, col)] for col in cols]


def table_from_header(cells, header_row: int, start_row: int):
    headers = row_values(cells, header_row)
    records = []
    row_number = start_row
    while True:
        values = row_values(cells, row_number)
        if not values:
            break
        record = {}
        for index, header in enumerate(headers):
            record[str(header)] = values[index] if index < len(values) else None
        records.append(record)
        row_number += 1
    return records


def keyed_table(cells, header_row: int, start_row: int, key_field: str):
    table = {}
    for record in table_from_header(cells, header_row, start_row):
        table[str(record[key_field])] = record
    return table


def expected_rows():
    _, sheets = load_workbook(WORKBOOK_PATH)

    prospects = table_from_header(sheets["Prospect Pool"], 2, 3)
    athletics = keyed_table(sheets["Athletic Testing"], 2, 3, "Prospect ID")
    splits = keyed_table(sheets["Game Splits"], 2, 3, "Prospect ID")
    positions = keyed_table(sheets["Position Coefficients"], 1, 2, "Position")
    discounts = keyed_table(sheets["Availability Discounts"], 1, 2, "Injury Band")
    rules = keyed_table(sheets["Board Rules"], 1, 2, "Rule")

    min_minutes = int(rules["Min Minutes"]["Value"])
    shortlist_size = int(rules["Shortlist Size"]["Value"])

    ranked = []
    for prospect in prospects:
        if str(prospect["Eligible"]) != "Y":
            continue
        if int(prospect["Scouted Minutes"]) < min_minutes:
            continue

        prospect_id = str(prospect["Prospect ID"])
        athletic_row = athletics[prospect_id]
        split_row = splits[prospect_id]
        position_row = positions[str(prospect["Position"])]
        discount_row = discounts[str(prospect["Injury Band"])]

        athletic_score = (
            0.40 * float(athletic_row["Burst Score"])
            + 0.35 * float(athletic_row["Movement Score"])
            + 0.25 * float(athletic_row["Strength Score"])
        )
        split_score = (
            0.20 * float(split_row["Early Grade"])
            + 0.50 * float(split_row["Conference Grade"])
            + 0.30 * float(split_row["Postseason Grade"])
            + float(split_row["Shot Creation Bonus"])
        )
        base_score = (
            athletic_score * float(position_row["Athletic Weight"])
            + split_score * float(position_row["Split Weight"])
            + float(position_row["Positional Bonus"])
            + float(prospect["Interview Bonus"])
        )
        composite_score = round(
            base_score * float(discount_row["Multiplier"])
            - float(discount_row["Availability Penalty"]),
            2,
        )

        ranked.append(
            {
                "prospect_id": prospect_id,
                "name": str(prospect["Name"]),
                "position": str(prospect["Position"]),
                "school": str(prospect["School"]),
                "injury_band": str(prospect["Injury Band"]),
                "conference_grade": float(split_row["Conference Grade"]),
                "composite_score": composite_score,
            }
        )

    ranked.sort(
        key=lambda item: (
            -item["composite_score"],
            -item["conference_grade"],
            item["prospect_id"],
        )
    )

    rows = []
    for index, item in enumerate(ranked[:shortlist_size], start=1):
        rows.append(
            {
                "rank": str(index),
                "prospect_id": item["prospect_id"],
                "name": item["name"],
                "position": item["position"],
                "school": item["school"],
                "injury_band": item["injury_band"],
                "composite_score": f"{item['composite_score']:.2f}",
            }
        )
    return rows


class TestOutputs:
    def test_workbook_exists(self):
        assert os.path.exists(WORKBOOK_PATH), f"Missing workbook: {WORKBOOK_PATH}"

    def test_workbook_layout(self):
        sheet_names, sheets = load_workbook(WORKBOOK_PATH)
        assert sheet_names == [
            "Prospect Pool",
            "Athletic Testing",
            "Game Splits",
            "Position Coefficients",
            "Availability Discounts",
            "Board Rules",
            "Historical Board",
        ]
        rules = keyed_table(sheets["Board Rules"], 1, 2, "Rule")
        assert int(rules["Min Minutes"]["Value"]) == 600
        assert int(rules["Shortlist Size"]["Value"]) == 5

    def test_expected_shortlist_from_workbook(self):
        rows = expected_rows()
        assert len(rows) == 5
        assert rows[0]["prospect_id"] == "DB-107"
        assert rows[-1]["prospect_id"] == "DB-109"

    def test_output_exists(self):
        assert os.path.exists(OUTPUT_PATH), f"Missing output file: {OUTPUT_PATH}"

    def test_output_header_and_shape(self):
        with open(OUTPUT_PATH, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            assert reader.fieldnames == EXPECTED_HEADER
            rows = list(reader)

        assert len(rows) == 5
        for expected_rank, row in enumerate(rows, start=1):
            assert row["rank"] == str(expected_rank)
            assert re.fullmatch(r"\d+\.\d{2}", row["composite_score"]), (
                f"composite_score must have exactly two decimals, got {row['composite_score']!r}"
            )

    def test_output_matches_expected(self):
        with open(OUTPUT_PATH, "r", encoding="utf-8", newline="") as f:
            actual_rows = list(csv.DictReader(f))

        assert actual_rows == expected_rows()
