import os
import tempfile
import unittest
import zipfile
from io import BytesIO
from xml.etree import ElementTree as ET

RESULT_FILE = os.environ.get("RESULT_FILE", "/root/revenue-forecast-refresh.pptx")
INPUT_FILE = os.environ.get("INPUT_FILE", "/root/sales-forecast-deck.pptx")

EMBEDDED_XLSX = "ppt/embeddings/Microsoft_Excel_Worksheet.xlsx"
XLSX_NS = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}

EXPECTED_UPDATES = {
    "D2": 13.4,
    "E3": 11.2,
    "C5": 9.1,
}

EXPECTED_TOTALS = {
    "B6": 41.9,
    "C6": 43.5,
    "D6": 44.6,
    "E6": 46.4,
}


def extract_workbook_bytes(pptx_path):
    with zipfile.ZipFile(pptx_path, "r") as zf:
        return zf.read(EMBEDDED_XLSX)


def load_sheet_state(pptx_path):
    workbook_bytes = extract_workbook_bytes(pptx_path)
    with zipfile.ZipFile(BytesIO(workbook_bytes), "r") as xzf:
        shared_root = ET.fromstring(xzf.read("xl/sharedStrings.xml"))
        shared_strings = []
        for item in shared_root.findall("x:si", XLSX_NS):
            shared_strings.append("".join(node.text or "" for node in item.findall(".//x:t", XLSX_NS)))

        sheet_root = ET.fromstring(xzf.read("xl/worksheets/sheet1.xml"))
        values = {}
        formulas = {}
        for cell in sheet_root.findall(".//x:c", XLSX_NS):
            ref = cell.attrib["r"]
            formula_node = cell.find("x:f", XLSX_NS)
            value_node = cell.find("x:v", XLSX_NS)
            if formula_node is not None:
                formulas[ref] = formula_node.text
            if value_node is None:
                continue
            if cell.attrib.get("t") == "s":
                values[ref] = shared_strings[int(value_node.text)]
            else:
                values[ref] = float(value_node.text)
        return values, formulas


class ForecastRefreshTests(unittest.TestCase):
    def test_output_file_exists(self):
        self.assertTrue(os.path.exists(RESULT_FILE), f"Missing output file: {RESULT_FILE}")

    def test_output_is_valid_pptx(self):
        self.assertTrue(zipfile.is_zipfile(RESULT_FILE), "Output is not a valid PPTX file")

    def test_embedded_workbook_still_exists(self):
        with zipfile.ZipFile(RESULT_FILE, "r") as zf:
            self.assertIn(EMBEDDED_XLSX, zf.namelist())

    def test_target_cells_are_updated(self):
        values, _formulas = load_sheet_state(RESULT_FILE)
        for cell_ref, expected in EXPECTED_UPDATES.items():
            self.assertAlmostEqual(values[cell_ref], expected, places=3, msg=f"{cell_ref} was not refreshed correctly")

    def test_total_row_cached_values_are_updated(self):
        values, _formulas = load_sheet_state(RESULT_FILE)
        for cell_ref, expected in EXPECTED_TOTALS.items():
            self.assertAlmostEqual(values[cell_ref], expected, places=3, msg=f"{cell_ref} total is incorrect")

    def test_total_formulas_are_preserved(self):
        _input_values, input_formulas = load_sheet_state(INPUT_FILE)
        _output_values, output_formulas = load_sheet_state(RESULT_FILE)
        for cell_ref in ["B6", "C6", "D6", "E6"]:
            self.assertEqual(input_formulas[cell_ref], output_formulas[cell_ref], f"Formula in {cell_ref} changed unexpectedly")

    def test_other_numeric_cells_stay_the_same(self):
        input_values, _ = load_sheet_state(INPUT_FILE)
        output_values, _ = load_sheet_state(RESULT_FILE)
        changed_cells = set(EXPECTED_UPDATES) | {"C6", "D6", "E6"}
        for cell_ref, value in input_values.items():
            if cell_ref in changed_cells:
                continue
            if isinstance(value, float):
                self.assertAlmostEqual(output_values[cell_ref], value, places=3, msg=f"{cell_ref} was modified unexpectedly")


if __name__ == "__main__":
    unittest.main()
