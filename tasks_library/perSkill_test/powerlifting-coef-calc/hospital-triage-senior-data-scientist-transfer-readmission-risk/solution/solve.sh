#!/bin/bash

set -euo pipefail

export TASK_OUTPUT_FILE="${TASK_OUTPUT_FILE:-/root/data/readmission_risk_dashboard.xlsx}"

python3 <<'PY'
import os
from pathlib import Path
from statistics import median
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile


INPUT_FILE = Path(os.environ["TASK_OUTPUT_FILE"])
NS_MAIN = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
AGE_PRIORITY = {"80+": 3, "65-79": 2, "50-64": 1, "<50": 0}


def excel_col_name(index: int) -> str:
    result = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


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
            target = rels[sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]]
            rows = parse_sheet_strings(zf.read(f"xl/{target}"))
            sheets.append((name, rows))
    return sheets


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


def round_half_up(value: float, digits: int) -> float:
    scale = 10 ** digits
    adjusted = value * scale
    if adjusted >= 0:
        adjusted = int(adjusted + 0.5)
    else:
        adjusted = int(adjusted - 0.5)
    return adjusted / scale


def build_outputs(admissions_rows):
    headers = admissions_rows[0]
    data_rows = [dict(zip(headers, row, strict=True)) for row in admissions_rows[1:]]

    risk_headers = [
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
    risk_rows = [risk_headers]

    detail_records = []
    for row in data_rows:
        band = age_band(int(row["Age"]))
        age_pts = age_points(band)
        prior_pts = prior_points(int(row["PriorAdmissions90D"]))
        tachycardia = 1 if int(row["HeartRate"]) >= 110 else 0
        hypotension = 1 if int(row["SystolicBP"]) < 100 else 0
        tachypnea = 1 if int(row["RespiratoryRate"]) >= 24 else 0
        hypoxia = 1 if int(row["OxygenSaturation"]) < 94 else 0
        fever = 1 if float(row["TemperatureC"]) >= 38.0 else 0
        high_charlson = 1 if int(row["CharlsonIndex"]) >= 5 else 0
        comorbidity_count = (
            int(row["HasCOPD"])
            + int(row["HasCHF"])
            + int(row["HasDiabetes"])
            + int(row["HasCKD"])
        )
        score = (
            age_pts
            + prior_pts
            + 2 * tachycardia
            + 2 * hypotension
            + tachypnea
            + 2 * hypoxia
            + fever
            + 2 * high_charlson
            + comorbidity_count
        )
        tier = risk_tier(score)
        record = {
            "AdmissionID": row["AdmissionID"],
            "Ward": row["Ward"],
            "Age": int(row["Age"]),
            "AgeBand": band,
            "AgePoints": age_pts,
            "PriorAdmissions90D": int(row["PriorAdmissions90D"]),
            "PriorAdmissionPoints": prior_pts,
            "HeartRate": int(row["HeartRate"]),
            "SystolicBP": int(row["SystolicBP"]),
            "RespiratoryRate": int(row["RespiratoryRate"]),
            "OxygenSaturation": int(row["OxygenSaturation"]),
            "TemperatureC": round_half_up(float(row["TemperatureC"]), 1),
            "TachycardiaFlag": tachycardia,
            "HypotensionFlag": hypotension,
            "TachypneaFlag": tachypnea,
            "HypoxiaFlag": hypoxia,
            "FeverFlag": fever,
            "CharlsonIndex": int(row["CharlsonIndex"]),
            "HighCharlsonFlag": high_charlson,
            "ComorbidityCount": comorbidity_count,
            "ReadmissionRiskScore": score,
            "RiskTier": tier,
        }
        detail_records.append(record)
        risk_rows.append([record[column] for column in risk_headers])

    summary_headers = [
        "Ward",
        "PatientCount",
        "AvgRiskScore",
        "HighRiskPatients",
        "HighRiskSharePct",
        "MedianCharlsonIndex",
        "MostCommonAgeBand",
        "EscalationNeeded",
    ]
    summary_rows = [summary_headers]
    wards = sorted({record["Ward"] for record in detail_records})
    for ward in wards:
        ward_records = [record for record in detail_records if record["Ward"] == ward]
        patient_count = len(ward_records)
        avg_score = round_half_up(
            sum(record["ReadmissionRiskScore"] for record in ward_records) / patient_count,
            2,
        )
        high_risk_patients = sum(1 for record in ward_records if record["RiskTier"] == "High")
        high_risk_share = round_half_up(high_risk_patients * 100 / patient_count, 1)
        median_charlson = round_half_up(
            float(median(record["CharlsonIndex"] for record in ward_records)),
            1,
        )

        age_band_counts = {}
        for record in ward_records:
            age_band_counts[record["AgeBand"]] = age_band_counts.get(record["AgeBand"], 0) + 1
        most_common_age_band = sorted(
            age_band_counts.items(),
            key=lambda item: (item[1], AGE_PRIORITY[item[0]]),
            reverse=True,
        )[0][0]

        escalation = "Yes" if avg_score >= 10 or high_risk_patients >= 2 else "No"
        summary_rows.append(
            [
                ward,
                patient_count,
                avg_score,
                high_risk_patients,
                high_risk_share,
                median_charlson,
                most_common_age_band,
                escalation,
            ]
        )

    admissions_output = [admissions_rows[0], *[list(row.values()) for row in data_rows]]
    return [
        ("Admissions", admissions_output),
        ("RiskScoring", risk_rows),
        ("WardSummary", summary_rows),
    ]


def cell_xml(value, ref: str) -> str:
    if value == "":
        return f'<c r="{ref}"/>'
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f'<c r="{ref}" t="n"><v>{value}</v></c>'
    return f'<c r="{ref}" t="inlineStr"><is><t>{escape(str(value))}</t></is></c>'


def worksheet_xml(rows):
    row_xml = []
    max_cols = max((len(row) for row in rows), default=1)
    last_cell = f"{excel_col_name(max_cols)}{max(len(rows), 1)}"
    for row_idx, row in enumerate(rows, start=1):
        cells = [cell_xml(value, f"{excel_col_name(col_idx)}{row_idx}") for col_idx, value in enumerate(row, start=1)]
        row_xml.append(f'<row r="{row_idx}">{"".join(cells)}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<dimension ref="A1:{last_cell}"/>'
        '<sheetViews><sheetView workbookViewId="0"/></sheetViews>'
        '<sheetFormatPr defaultRowHeight="15"/>'
        f'<sheetData>{"".join(row_xml)}</sheetData>'
        '</worksheet>'
    )


def write_workbook(path: Path, sheets):
    content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
  <Override PartName="/xl/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/worksheets/sheet3.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>'''

    rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>'''

    workbook_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="Admissions" sheetId="1" r:id="rId1"/>
    <sheet name="RiskScoring" sheetId="2" r:id="rId2"/>
    <sheet name="WardSummary" sheetId="3" r:id="rId3"/>
  </sheets>
</workbook>'''

    workbook_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet3.xml"/>
  <Relationship Id="rId4" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
  <Relationship Id="rId5" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="theme/theme1.xml"/>
</Relationships>'''

    styles = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>
  <fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills>
  <borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs>
  <cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>'''

    theme = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="Office Theme">
  <a:themeElements>
    <a:clrScheme name="Office"><a:dk1><a:sysClr val="windowText" lastClr="000000"/></a:dk1><a:lt1><a:sysClr val="window" lastClr="FFFFFF"/></a:lt1><a:dk2><a:srgbClr val="1F497D"/></a:dk2><a:lt2><a:srgbClr val="EEECE1"/></a:lt2><a:accent1><a:srgbClr val="4F81BD"/></a:accent1><a:accent2><a:srgbClr val="C0504D"/></a:accent2><a:accent3><a:srgbClr val="9BBB59"/></a:accent3><a:accent4><a:srgbClr val="8064A2"/></a:accent4><a:accent5><a:srgbClr val="4BACC6"/></a:accent5><a:accent6><a:srgbClr val="F79646"/></a:accent6><a:hlink><a:srgbClr val="0000FF"/></a:hlink><a:folHlink><a:srgbClr val="800080"/></a:folHlink></a:clrScheme>
    <a:fontScheme name="Office"><a:majorFont><a:latin typeface="Calibri"/></a:majorFont><a:minorFont><a:latin typeface="Calibri"/></a:minorFont></a:fontScheme>
    <a:fmtScheme name="Office"><a:fillStyleLst/><a:lnStyleLst/><a:effectStyleLst/><a:bgFillStyleLst/></a:fmtScheme>
  </a:themeElements>
</a:theme>'''

    core = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>Readmission Risk Dashboard</dc:title>
  <dc:creator>OpenAI</dc:creator>
  <cp:lastModifiedBy>OpenAI</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">2026-03-22T00:00:00Z</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">2026-03-22T00:00:00Z</dcterms:modified>
</cp:coreProperties>'''

    app = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>OpenAI</Application>
</Properties>'''

    with ZipFile(path, "w", ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", rels)
        zf.writestr("docProps/core.xml", core)
        zf.writestr("docProps/app.xml", app)
        zf.writestr("xl/workbook.xml", workbook_xml)
        zf.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        zf.writestr("xl/styles.xml", styles)
        zf.writestr("xl/theme/theme1.xml", theme)
        for sheet_index, (_, rows) in enumerate(sheets, start=1):
            zf.writestr(f"xl/worksheets/sheet{sheet_index}.xml", worksheet_xml(rows))


workbook_sheets = load_workbook(INPUT_FILE)
admissions_rows = dict(workbook_sheets)["Admissions"]
updated_sheets = build_outputs(admissions_rows)
write_workbook(INPUT_FILE, updated_sheets)
PY
