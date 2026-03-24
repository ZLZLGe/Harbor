import json
import os
import re
import xml.etree.ElementTree as ET
from zipfile import ZipFile


WORKBOOK_PATH = "/root/cold_chain_routes.xlsx"
OUTPUT_PATH = "/root/route_alerts.json"

NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "pkg": "http://schemas.openxmlformats.org/package/2006/relationships",
}

RISK_ORDER = {"Critical": 0, "High": 1, "Moderate": 2, "Low": 3}


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


def load_workbook(path: str) -> dict[str, dict[tuple[int, int], object]]:
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
            sheets[sheet.attrib["name"]] = parse_sheet(zf.read(target))
    return sheets


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
        if len(values) == 1 and values[0] == "ACTIVE ROUTES END":
            break
        if values == headers:
            row_number += 1
            continue
        record = {}
        for index, header in enumerate(headers):
            record[header] = values[index] if index < len(values) else None
        records.append(record)
        row_number += 1
    return records


def keyed_table(cells, header_row: int, start_row: int, key_field: str):
    table = {}
    for record in table_from_header(cells, header_row, start_row):
        table[str(record[key_field])] = record
    return table


def risk_level(score: int, lane_row: dict[str, object]) -> str:
    if score >= int(lane_row["Critical Score"]):
        return "Critical"
    if score >= int(lane_row["High Score"]):
        return "High"
    if score >= 4:
        return "Moderate"
    return "Low"


def expected_output():
    sheets = load_workbook(WORKBOOK_PATH)
    dispatch = sheets["Dispatch Log"]
    start_row = next(
        row
        for (row, col), value in dispatch.items()
        if col == 1 and value == "ACTIVE ROUTES START"
    )
    active_routes = table_from_header(dispatch, start_row + 1, start_row + 2)

    contracts = keyed_table(sheets["Contract Terms"], 2, 3, "Contract ID")
    lanes = keyed_table(sheets["Lane Thresholds"], 1, 2, "Lane")
    clients = keyed_table(sheets["Client Priority"], 1, 2, "Client Code")

    routes_to_escalate = []
    for route in active_routes:
        contract = contracts[str(route["Contract ID"])]
        lane = lanes[str(route["Lane"])]
        client = clients[str(route["Client Code"])]

        planned = int(route["Planned Stops"])
        on_time = int(route["On-Time Stops"])
        late = int(route["Late Stops"])
        temp = int(route["Temp Excursions"])
        overrun = float(route["Max Temp Overrun C"])
        spoilage = int(route["Spoilage Crates"])
        revenue = float(route["Revenue"])
        linehaul = float(route["Linehaul Cost"])
        cooling = float(route["Cooling Cost"])

        on_time_ratio = on_time / planned
        late_penalty = late * float(contract["Late Penalty Per Stop"])
        temp_penalty = temp * float(contract["Temp Penalty Per Excursion"])
        if temp > 0 and overrun >= float(lane["Critical Overrun C"]):
            temp_penalty *= float(contract["Severe Temp Multiplier"])
        spoilage_penalty = spoilage * float(contract["Spoilage Penalty Per Crate"])
        rebate_penalty = 0.0
        if on_time_ratio < float(contract["Min On-Time Ratio"]):
            rebate_penalty = revenue * float(contract["Rebate Pct"])

        adjusted_profit = round(
            float(
                revenue
                - linehaul
                - cooling
                - late_penalty
                - temp_penalty
                - spoilage_penalty
                - rebate_penalty
            ),
            2,
        )

        if overrun >= float(lane["Critical Overrun C"]):
            overrun_bonus = int(lane["Critical Bonus"])
        elif overrun >= float(lane["Warning Overrun C"]):
            overrun_bonus = int(lane["Warning Bonus"])
        else:
            overrun_bonus = 0

        score = (
            late * int(lane["Late Points"])
            + temp * int(lane["Temp Points"])
            + spoilage * int(lane["Spoilage Points"])
            + overrun_bonus
            + int(client["Priority Points"])
        )

        final_level = risk_level(score, lane)
        upgraded = False
        if (
            str(client["Priority Tier"]) == "Critical"
            and temp > 0
            and final_level == "Moderate"
        ):
            final_level = "High"
            upgraded = True

        reasons = []
        if adjusted_profit < float(client["Profit Floor"]):
            reasons.append("profit_below_floor")
        if temp > 0:
            reasons.append("temp_control_breach")
        if late > 0:
            reasons.append("service_failures")
        if spoilage > 0:
            reasons.append("spoilage_claim")
        if upgraded:
            reasons.append("priority_upgrade")

        if final_level in {"High", "Critical"} or adjusted_profit < float(client["Profit Floor"]):
            routes_to_escalate.append(
                {
                    "route_id": str(route["Route ID"]),
                    "lane": str(route["Lane"]),
                    "client_code": str(route["Client Code"]),
                    "priority_tier": str(client["Priority Tier"]),
                    "adjusted_profit": adjusted_profit,
                    "risk_score": score,
                    "risk_level": final_level,
                    "reasons": reasons,
                }
            )

    routes_to_escalate.sort(
        key=lambda item: (
            RISK_ORDER[item["risk_level"]],
            item["adjusted_profit"],
            item["route_id"],
        )
    )
    return {"routes_to_escalate": routes_to_escalate}


class TestOutputs:
    def test_workbook_exists(self):
        assert os.path.exists(WORKBOOK_PATH), f"Missing workbook: {WORKBOOK_PATH}"

    def test_workbook_has_active_and_archive_sections(self):
        sheets = load_workbook(WORKBOOK_PATH)
        dispatch = sheets["Dispatch Log"]
        first_col_text = [value for (row, col), value in sorted(dispatch.items()) if col == 1]
        assert "ACTIVE ROUTES START" in first_col_text
        assert "ACTIVE ROUTES END" in first_col_text
        assert "ARCHIVE - DO NOT USE" in first_col_text

    def test_expected_alert_count_from_workbook(self):
        expected = expected_output()
        assert len(expected["routes_to_escalate"]) == 6
        assert expected["routes_to_escalate"][0]["route_id"] == "RT-207"
        assert expected["routes_to_escalate"][-1]["route_id"] == "RT-209"

    def test_output_exists(self):
        assert os.path.exists(OUTPUT_PATH), f"Missing output file: {OUTPUT_PATH}"

    def test_output_shape(self):
        with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert isinstance(data, dict), "route_alerts.json must be a JSON object"
        assert set(data.keys()) == {"routes_to_escalate"}
        assert isinstance(data["routes_to_escalate"], list)

        for item in data["routes_to_escalate"]:
            assert set(item.keys()) == {
                "route_id",
                "lane",
                "client_code",
                "priority_tier",
                "adjusted_profit",
                "risk_score",
                "risk_level",
                "reasons",
            }
            assert item["risk_level"] in RISK_ORDER
            assert isinstance(item["reasons"], list)

    def test_output_matches_expected(self):
        with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
            actual = json.load(f)

        assert actual == expected_output()
