import os
import re
import xml.etree.ElementTree as ET
from zipfile import ZipFile


INPUT_PATH = "/root/icu_capacity_template"
OUTPUT_PATH = "/root/ward_capacity_model"

NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pkg": "http://schemas.openxmlformats.org/package/2006/relationships",
}

EXPECTED_WARD_VALUES = {
    "F6": 17,
    "F7": 13,
    "F8": 12,
    "F9": 9,
    "F10": 7,
    "G6": 20,
    "G7": 16,
    "G8": 14,
    "G9": 11,
    "G10": 9,
    "H6": 20,
    "H7": 16,
    "H8": 14,
    "H9": 12,
    "H10": 10,
    "I6": 0.85,
    "I7": 0.8125,
    "I8": 0.8571428571,
    "I9": 0.75,
    "I10": 0.7,
    "J6": 1.0,
    "J7": 1.0,
    "J8": 1.0,
    "J9": 0.9166666667,
    "J10": 0.9,
    "K6": 1.0,
    "K7": 1.0,
    "K8": 1.0,
    "K9": 1.0,
    "K10": 1.0,
}

EXPECTED_SUMMARY_VALUES = {
    "B5": 58,
    "B6": 14,
    "B7": 29,
    "B8": 6,
    "B9": 5,
    "B10": 31,
    "B11": 7,
    "B12": 6,
    "B13": 0.8571428571,
    "B14": 0,
    "C5": 70,
    "C6": 2,
    "C7": 40,
    "C8": 9,
    "C9": 6,
    "C10": 44,
    "C11": 10,
    "C12": 7,
    "C13": 1,
    "C14": 4,
    "D5": 72,
    "D6": 0,
    "D7": 47,
    "D8": 11,
    "D9": 8,
    "D10": 53,
    "D11": 13,
    "D12": 9,
    "D13": 1,
    "D14": 5,
}

TOL = 1e-9


def parse_scalar(raw: str | None):
    if raw is None or raw == "":
        return None
    if re.fullmatch(r"-?\d+", raw):
        return int(raw)
    return float(raw)


def load_workbook(path: str):
    with ZipFile(path) as zf:
        workbook = ET.fromstring(zf.read("xl/workbook.xml"))
        rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        target_by_id = {
            rel.attrib["Id"]: rel.attrib["Target"]
            for rel in rels.findall("pkg:Relationship", NS)
        }

        sheets = {}
        for sheet in workbook.find("main:sheets", NS):
            rel_id = sheet.attrib[
                "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
            ]
            target = "xl/" + target_by_id[rel_id]
            sheets[sheet.attrib["name"]] = ET.fromstring(zf.read(target))
        return sheets


def parse_sheet(root):
    cells = {}
    for row in root.findall("main:sheetData/main:row", NS):
        for cell in row.findall("main:c", NS):
            ref = cell.attrib["r"]
            formula = cell.findtext("main:f", default=None, namespaces=NS)
            raw_value = cell.findtext("main:v", default=None, namespaces=NS)
            inline = cell.find("main:is", NS)
            if inline is not None:
                text = "".join(node.text or "" for node in inline.findall(".//main:t", NS))
                value = text
            else:
                value = parse_scalar(raw_value)
            cells[ref] = {
                "formula": formula,
                "value": value,
                "style": int(cell.attrib["s"]) if "s" in cell.attrib else None,
            }
    return cells


def normalize_formula(text: str | None) -> str:
    if text is None:
        return ""
    return re.sub(r"\s+", "", text).replace(";", ",").upper()


def assert_close(actual, expected):
    assert actual is not None, f"Missing cached value, expected {expected}"
    assert abs(float(actual) - float(expected)) <= TOL, (
        f"Expected {expected}, got {actual}"
    )


class TestOutputs:
    def test_input_exists(self):
        assert os.path.exists(INPUT_PATH), f"Missing input workbook: {INPUT_PATH}"

    def test_input_template_is_incomplete(self):
        sheets = load_workbook(INPUT_PATH)
        ward = parse_sheet(sheets["Ward Load"])
        summary = parse_sheet(sheets["Staffing Summary"])
        assert ward["F6"]["formula"] is None
        assert summary["B5"]["formula"] is None

    def test_output_exists(self):
        assert os.path.exists(OUTPUT_PATH), f"Missing output workbook: {OUTPUT_PATH}"

    def test_output_has_required_sheets(self):
        sheets = load_workbook(OUTPUT_PATH)
        assert set(sheets.keys()) == {"Assumptions", "Ward Load", "Staffing Summary"}
        assert len(sheets) == 3

    def test_formula_coverage(self):
        sheets = load_workbook(OUTPUT_PATH)
        ward = parse_sheet(sheets["Ward Load"])
        summary = parse_sheet(sheets["Staffing Summary"])

        for row in range(6, 11):
            for col in ["F", "G", "H", "I", "J", "K"]:
                assert ward[f"{col}{row}"]["formula"], f"Missing formula in Ward Load!{col}{row}"

        for row in range(5, 15):
            for col in ["B", "C", "D"]:
                assert summary[f"{col}{row}"]["formula"], (
                    f"Missing formula in Staffing Summary!{col}{row}"
                )

    def test_ward_load_formulas_reference_assumptions(self):
        sheets = load_workbook(OUTPUT_PATH)
        ward = parse_sheet(sheets["Ward Load"])

        for row in range(6, 11):
            for census_col, occ_col, assumption_col in [("F", "I", "B"), ("G", "J", "C"), ("H", "K", "D")]:
                census_formula = normalize_formula(ward[f"{census_col}{row}"]["formula"])
                assert "MIN(" in census_formula
                assert "ROUND(" in census_formula
                assert f"D{row}" in census_formula
                assert f"E{row}" in census_formula
                assert re.search(rf"ASSUMPTIONS!\$?{assumption_col}\$?5", census_formula)
                assert re.search(rf"ASSUMPTIONS!\$?{assumption_col}\$?6", census_formula)

                occ_formula = normalize_formula(ward[f"{occ_col}{row}"]["formula"])
                assert f"{census_col}{row}" in occ_formula
                assert re.search(rf"\$?C{row}", occ_formula)

    def test_summary_formulas_reference_model(self):
        sheets = load_workbook(OUTPUT_PATH)
        summary = parse_sheet(sheets["Staffing Summary"])

        for scenario_col, ward_col, occ_col, assumption_col in [
            ("B", "F", "I", "B"),
            ("C", "G", "J", "C"),
            ("D", "H", "K", "D"),
        ]:
            total_formula = normalize_formula(summary[f"{scenario_col}5"]["formula"])
            assert re.search(rf"'?WARDLOAD'?!\$?{ward_col}\$?6:\$?{ward_col}\$?10", total_formula)

            available_formula = normalize_formula(summary[f"{scenario_col}6"]["formula"])
            assert "SUM('WARDLOAD'!$C$6:$C$10)".replace(" ", "") in available_formula
            assert f"{scenario_col}5" in available_formula

            rn_formula = normalize_formula(summary[f"{scenario_col}7"]["formula"])
            assert "ROUNDUP(" in rn_formula
            assert re.search(rf"ASSUMPTIONS!\$?{assumption_col}\$?7", rn_formula)
            assert re.search(rf"ASSUMPTIONS!\$?{assumption_col}\$?11", rn_formula)

            for row, assumption_row in [(8, 8), (9, 9), (10, 10), (11, 10), (12, 10)]:
                formula = normalize_formula(summary[f"{scenario_col}{row}"]["formula"])
                if row <= 9:
                    assert "ROUNDUP(" in formula
                assert re.search(rf"ASSUMPTIONS!\$?{assumption_col}\$?{assumption_row}", formula)

            max_formula = normalize_formula(summary[f"{scenario_col}13"]["formula"])
            assert "MAX(" in max_formula
            assert re.search(rf"'?WARDLOAD'?!\$?{occ_col}\$?6:\$?{occ_col}\$?10", max_formula)

            count_formula = normalize_formula(summary[f"{scenario_col}14"]["formula"])
            assert "COUNTIF(" in count_formula
            assert ">0.9" in count_formula

    def test_cached_values_match_expected(self):
        sheets = load_workbook(OUTPUT_PATH)
        ward = parse_sheet(sheets["Ward Load"])
        summary = parse_sheet(sheets["Staffing Summary"])

        for ref, expected in EXPECTED_WARD_VALUES.items():
            assert_close(ward[ref]["value"], expected)

        for ref, expected in EXPECTED_SUMMARY_VALUES.items():
            assert_close(summary[ref]["value"], expected)
