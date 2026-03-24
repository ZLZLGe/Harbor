import os
from collections import Counter
from pathlib import Path
from statistics import median
from xml.etree import ElementTree as ET
from zipfile import ZipFile


OUTPUT_FILE = Path(os.environ.get("TASK_OUTPUT_FILE", "/root/data/readmission_risk_dashboard.xlsx"))
NS_MAIN = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
AGE_PRIORITY = {"80+": 3, "65-79": 2, "50-64": 1, "<50": 0}
EXPECTED_RISK_COLUMNS = [
    "AdmissionID",
    "Ward",
    "Age",
    "AgeBand",
    "AgePoints",
    "PriorAdmissions90D",
    "PriorAdmissionPoints",
    "HeartRate",
    "SystolicBP",
    "RespiratoryRate",
    "OxygenSaturation",
    "TemperatureC",
    "TachycardiaFlag",
    "HypotensionFlag",
    "TachypneaFlag",
    "HypoxiaFlag",
    "FeverFlag",
    "CharlsonIndex",
    "HighCharlsonFlag",
    "ComorbidityCount",
    "ReadmissionRiskScore",
    "RiskTier",
]
EXPECTED_WARD_COLUMNS = [
    "Ward",
    "PatientCount",
    "AvgRiskScore",
    "HighRiskPatients",
    "HighRiskSharePct",
    "MedianCharlsonIndex",
    "MostCommonAgeBand",
    "EscalationNeeded",
]


def coerce_value(text: str):
    if text is None or text == "":
        return ""
    try:
        return int(text)
    except ValueError:
        try:
            value = float(text)
        except ValueError:
            return text
        return int(value) if value.is_integer() else value


def parse_sheet_strings(sheet_xml: bytes):
    root = ET.fromstring(sheet_xml)
    rows = []
    for row in root.findall(".//main:sheetData/main:row", NS_MAIN):
        values = []
        for cell in row.findall("main:c", NS_MAIN):
            cell_type = cell.attrib.get("t")
            if cell_type == "inlineStr":
                text = "".join(cell.itertext())
            else:
                value_node = cell.find("main:v", NS_MAIN)
                text = value_node.text if value_node is not None else ""
            values.append(coerce_value(text))
        rows.append(values)
    return rows


def load_workbook(path: Path):
    with ZipFile(path) as zf:
        workbook_root = ET.fromstring(zf.read("xl/workbook.xml"))
        rel_root = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        rels = {
            rel.attrib["Id"]: rel.attrib["Target"]
            for rel in rel_root
            if rel.attrib.get("Type", "").endswith("/worksheet")
        }
        sheets = []
        for sheet in workbook_root.findall("main:sheets/main:sheet", NS_MAIN):
            name = sheet.attrib["name"]
            rel_id = sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
            rows = parse_sheet_strings(zf.read(f"xl/{rels[rel_id]}"))
            sheets.append((name, rows))
    return sheets


def round_half_up(value: float, digits: int) -> float:
    scale = 10 ** digits
    adjusted = value * scale
    if adjusted >= 0:
        adjusted = int(adjusted + 0.5)
    else:
        adjusted = int(adjusted - 0.5)
    return adjusted / scale


def age_band(age: int) -> str:
    if age < 50:
        return "<50"
    if age <= 64:
        return "50-64"
    if age <= 79:
        return "65-79"
    return "80+"


def age_points(band: str) -> int:
    return {"<50": 0, "50-64": 1, "65-79": 2, "80+": 3}[band]


def prior_points(prior_admissions: int) -> int:
    if prior_admissions == 0:
        return 0
    if prior_admissions == 1:
        return 2
    return 4


def risk_tier(score: int) -> str:
    if score <= 4:
        return "Low"
    if score <= 9:
        return "Medium"
    return "High"


def rows_to_dicts(rows):
    headers = rows[0]
    return [dict(zip(headers, row, strict=True)) for row in rows[1:]]


def build_expected(admissions_rows):
    admissions = rows_to_dicts(admissions_rows)
    detail_rows = []
    for row in admissions:
        band = age_band(int(row["Age"]))
        score = (
            age_points(band)
            + prior_points(int(row["PriorAdmissions90D"]))
            + 2 * (1 if int(row["HeartRate"]) >= 110 else 0)
            + 2 * (1 if int(row["SystolicBP"]) < 100 else 0)
            + (1 if int(row["RespiratoryRate"]) >= 24 else 0)
            + 2 * (1 if int(row["OxygenSaturation"]) < 94 else 0)
            + (1 if float(row["TemperatureC"]) >= 38.0 else 0)
            + 2 * (1 if int(row["CharlsonIndex"]) >= 5 else 0)
            + int(row["HasCOPD"])
            + int(row["HasCHF"])
            + int(row["HasDiabetes"])
            + int(row["HasCKD"])
        )
        detail_rows.append(
            {
                "AdmissionID": row["AdmissionID"],
                "Ward": row["Ward"],
                "Age": int(row["Age"]),
                "AgeBand": band,
                "AgePoints": age_points(band),
                "PriorAdmissions90D": int(row["PriorAdmissions90D"]),
                "PriorAdmissionPoints": prior_points(int(row["PriorAdmissions90D"])),
                "HeartRate": int(row["HeartRate"]),
                "SystolicBP": int(row["SystolicBP"]),
                "RespiratoryRate": int(row["RespiratoryRate"]),
                "OxygenSaturation": int(row["OxygenSaturation"]),
                "TemperatureC": round_half_up(float(row["TemperatureC"]), 1),
                "TachycardiaFlag": 1 if int(row["HeartRate"]) >= 110 else 0,
                "HypotensionFlag": 1 if int(row["SystolicBP"]) < 100 else 0,
                "TachypneaFlag": 1 if int(row["RespiratoryRate"]) >= 24 else 0,
                "HypoxiaFlag": 1 if int(row["OxygenSaturation"]) < 94 else 0,
                "FeverFlag": 1 if float(row["TemperatureC"]) >= 38.0 else 0,
                "CharlsonIndex": int(row["CharlsonIndex"]),
                "HighCharlsonFlag": 1 if int(row["CharlsonIndex"]) >= 5 else 0,
                "ComorbidityCount": int(row["HasCOPD"]) + int(row["HasCHF"]) + int(row["HasDiabetes"]) + int(row["HasCKD"]),
                "ReadmissionRiskScore": score,
                "RiskTier": risk_tier(score),
            }
        )

    ward_rows = []
    for ward in sorted({row["Ward"] for row in detail_rows}):
        records = [row for row in detail_rows if row["Ward"] == ward]
        age_counts = Counter(row["AgeBand"] for row in records)
        most_common_age_band = sorted(
            age_counts.items(),
            key=lambda item: (item[1], AGE_PRIORITY[item[0]]),
            reverse=True,
        )[0][0]
        high_risk_patients = sum(1 for row in records if row["RiskTier"] == "High")
        avg_risk_score = round_half_up(
            sum(row["ReadmissionRiskScore"] for row in records) / len(records),
            2,
        )
        ward_rows.append(
            {
                "Ward": ward,
                "PatientCount": len(records),
                "AvgRiskScore": avg_risk_score,
                "HighRiskPatients": high_risk_patients,
                "HighRiskSharePct": round_half_up(high_risk_patients * 100 / len(records), 1),
                "MedianCharlsonIndex": round_half_up(float(median(row["CharlsonIndex"] for row in records)), 1),
                "MostCommonAgeBand": most_common_age_band,
                "EscalationNeeded": "Yes" if avg_risk_score >= 10 or high_risk_patients >= 2 else "No",
            }
        )

    return detail_rows, ward_rows


def test_workbook_has_required_sheets_in_order():
    workbook = load_workbook(OUTPUT_FILE)
    assert [name for name, _ in workbook] == ["Admissions", "RiskScoring", "WardSummary"]


def test_output_headers_match_spec():
    workbook = dict(load_workbook(OUTPUT_FILE))
    assert workbook["RiskScoring"][0] == EXPECTED_RISK_COLUMNS
    assert workbook["WardSummary"][0] == EXPECTED_WARD_COLUMNS


def test_admissions_sheet_is_preserved():
    workbook = dict(load_workbook(OUTPUT_FILE))
    admissions = rows_to_dicts(workbook["Admissions"])
    assert len(admissions) == 12
    assert admissions[0]["AdmissionID"] == "A1001"
    assert admissions[-1]["AdmissionID"] == "A1012"


def test_risk_scoring_matches_expected_values():
    workbook = dict(load_workbook(OUTPUT_FILE))
    expected_risk, _ = build_expected(workbook["Admissions"])
    actual_risk = rows_to_dicts(workbook["RiskScoring"])
    assert actual_risk == expected_risk


def test_ward_summary_matches_expected_values():
    workbook = dict(load_workbook(OUTPUT_FILE))
    _, expected_summary = build_expected(workbook["Admissions"])
    actual_summary = rows_to_dicts(workbook["WardSummary"])
    assert actual_summary == expected_summary


def test_risk_tier_distribution_and_escalation_flags():
    workbook = dict(load_workbook(OUTPUT_FILE))
    actual_risk = rows_to_dicts(workbook["RiskScoring"])
    actual_summary = rows_to_dicts(workbook["WardSummary"])

    tier_counts = Counter(row["RiskTier"] for row in actual_risk)
    assert tier_counts == {"High": 5, "Medium": 3, "Low": 4}

    escalation = {row["Ward"]: row["EscalationNeeded"] for row in actual_summary}
    assert escalation == {
        "Cardiology": "Yes",
        "General Medicine": "Yes",
        "Nephrology": "No",
        "Orthopedics": "No",
        "Pulmonology": "No",
    }
