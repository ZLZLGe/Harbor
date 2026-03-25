#!/bin/bash
set -euo pipefail

cd /root

python3 - <<'PY'
import csv
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from xml.sax.saxutils import escape


OUTPUT = Path("reservoir-resilience-model.xlsx")

POLICY = [
    ("Initial_Storage_MCM", 188.0),
    ("Max_Storage_MCM", 240.0),
    ("Dead_Storage_MCM", 70.0),
    ("Emergency_Floor_MCM", 52.0),
    ("Watch_Threshold_MCM", 130.0),
    ("Emergency_Threshold_MCM", 96.0),
    ("Urban_Watch_Factor", 0.96),
    ("Urban_Emergency_Factor", 0.90),
    ("Agriculture_Watch_Factor", 0.82),
    ("Agriculture_Emergency_Factor", 0.60),
    ("Emergency_Buffer_Max_MCM", 18.0),
    ("Target_End_Storage_MCM", 88.0),
]


def col_letter(n: int) -> str:
    result = ""
    while n:
        n, rem = divmod(n - 1, 26)
        result = chr(65 + rem) + result
    return result


def cell_xml(ref, value=None, cell_type=None, formula=None):
    attrs = [f'r="{ref}"']
    if cell_type == "inlineStr":
        attrs.append('t="inlineStr"')
    elif cell_type:
        attrs.append(f't="{cell_type}"')
    parts = [f'<c {" ".join(attrs)}>']
    if formula is not None:
        parts.append(f"<f>{escape(formula)}</f>")
    if cell_type == "inlineStr":
        text = "" if value is None else escape(str(value))
        parts.append(f"<is><t>{text}</t></is>")
    elif value is not None:
        parts.append(f"<v>{escape(str(value))}</v>")
    parts.append("</c>")
    return "".join(parts)


def row_xml(row_idx, values):
    cells = []
    for col_idx, spec in enumerate(values, start=1):
        if spec is None:
            continue
        ref = f"{col_letter(col_idx)}{row_idx}"
        if isinstance(spec, dict):
            cells.append(cell_xml(ref, spec.get("value"), spec.get("type"), spec.get("formula")))
        elif isinstance(spec, (int, float)):
            cells.append(cell_xml(ref, spec))
        else:
            cells.append(cell_xml(ref, spec, "inlineStr"))
    return f'<row r="{row_idx}">{"".join(cells)}</row>'


def sheet_xml(rows):
    max_col = 1
    for row in rows:
        if row:
            max_col = max(max_col, len(row))
    dim = f"A1:{col_letter(max_col)}{len(rows)}"
    body = "".join(row_xml(idx, row) for idx, row in enumerate(rows, start=1))
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<dimension ref="{dim}"/>'
        '<sheetViews><sheetView workbookViewId="0"/></sheetViews>'
        '<sheetFormatPr defaultRowHeight="15"/>'
        f"<sheetData>{body}</sheetData>"
        "</worksheet>"
    )


with open("monthly_hydrology.csv", newline="", encoding="utf-8") as f:
    hydrology = list(csv.DictReader(f))

with open("water_demand.csv", newline="", encoding="utf-8") as f:
    demand = list(csv.DictReader(f))

policy = dict(POLICY)

monthly_rows = []
start_storage = policy["Initial_Storage_MCM"]
quarters = ["Q1"] * 3 + ["Q2"] * 3 + ["Q3"] * 3 + ["Q4"] * 3

for idx, (hydro, dem, quarter) in enumerate(zip(hydrology, demand, quarters), start=2):
    inflow = float(hydro["Inflow_MCM"])
    evap = float(hydro["Evaporation_Loss_MCM"])
    urban = float(dem["Urban_Demand_MCM"])
    agriculture = float(dem["Agriculture_Demand_MCM"])
    eco = float(dem["Eco_Min_Release_MCM"])

    if start_storage < policy["Emergency_Threshold_MCM"]:
        trigger_state = "Emergency"
        urban_factor = policy["Urban_Emergency_Factor"]
        ag_factor = policy["Agriculture_Emergency_Factor"]
    elif start_storage < policy["Watch_Threshold_MCM"]:
        trigger_state = "Watch"
        urban_factor = policy["Urban_Watch_Factor"]
        ag_factor = policy["Agriculture_Watch_Factor"]
    else:
        trigger_state = "Normal"
        urban_factor = 1.0
        ag_factor = 1.0

    urban_target = urban * urban_factor
    ag_target = agriculture * ag_factor
    planned_release = eco + urban_target + ag_target
    base_usable = max(start_storage + inflow - evap - policy["Dead_Storage_MCM"], 0.0)
    max_extra = max(max(start_storage + inflow - evap - policy["Emergency_Floor_MCM"], 0.0) - base_usable, 0.0)

    if trigger_state == "Emergency":
        emergency_used = min(
            policy["Emergency_Buffer_Max_MCM"],
            max(0.0, planned_release - base_usable),
            max_extra,
        )
    else:
        emergency_used = 0.0

    feasible_release = min(planned_release, base_usable + emergency_used)
    eco_actual = min(eco, feasible_release)
    urban_actual = min(urban_target, max(feasible_release - eco_actual, 0.0))
    ag_actual = min(ag_target, max(feasible_release - eco_actual - urban_actual, 0.0))
    urban_shortage = urban - urban_actual
    ag_shortage = agriculture - ag_actual
    eco_shortage = eco - eco_actual
    total_shortage = urban_shortage + ag_shortage + eco_shortage
    end_storage = min(
        policy["Max_Storage_MCM"],
        start_storage + inflow - evap - eco_actual - urban_actual - ag_actual,
    )

    monthly_rows.append(
        {
            "row": idx,
            "month": hydro["Month"],
            "quarter": quarter,
            "inflow": inflow,
            "evap": evap,
            "urban_demand": urban,
            "ag_demand": agriculture,
            "eco_demand": eco,
            "start_storage": start_storage,
            "trigger_state": trigger_state,
            "urban_target": urban_target,
            "ag_target": ag_target,
            "emergency_used": emergency_used,
            "planned_release": planned_release,
            "base_usable": base_usable,
            "feasible_release": feasible_release,
            "eco_actual": eco_actual,
            "urban_actual": urban_actual,
            "ag_actual": ag_actual,
            "urban_shortage": urban_shortage,
            "ag_shortage": ag_shortage,
            "eco_shortage": eco_shortage,
            "total_shortage": total_shortage,
            "end_storage": end_storage,
        }
    )
    start_storage = end_storage

quarter_shortage = {key: 0.0 for key in ("Q1", "Q2", "Q3", "Q4")}
for item in monthly_rows:
    quarter_shortage[item["quarter"]] += item["total_shortage"]

summary = {
    "total_inflow": sum(item["inflow"] for item in monthly_rows),
    "total_urban_demand": sum(item["urban_demand"] for item in monthly_rows),
    "total_ag_demand": sum(item["ag_demand"] for item in monthly_rows),
    "total_eco_demand": sum(item["eco_demand"] for item in monthly_rows),
    "total_urban_actual": sum(item["urban_actual"] for item in monthly_rows),
    "total_ag_actual": sum(item["ag_actual"] for item in monthly_rows),
    "total_eco_actual": sum(item["eco_actual"] for item in monthly_rows),
    "total_shortage": sum(item["total_shortage"] for item in monthly_rows),
    "watch_months": sum(1 for item in monthly_rows if item["trigger_state"] == "Watch"),
    "emergency_months": sum(1 for item in monthly_rows if item["trigger_state"] == "Emergency"),
    "buffer_months": sum(1 for item in monthly_rows if item["emergency_used"] > 0),
    "min_end_storage": min(item["end_storage"] for item in monthly_rows),
    "end_storage": monthly_rows[-1]["end_storage"],
}
summary["urban_service_ratio"] = summary["total_urban_actual"] / summary["total_urban_demand"]
summary["ag_service_ratio"] = summary["total_ag_actual"] / summary["total_ag_demand"]
summary["eco_compliance_ratio"] = summary["total_eco_actual"] / summary["total_eco_demand"]
summary["end_gap"] = summary["end_storage"] - policy["Target_End_Storage_MCM"]
summary["q3_share"] = 0.0 if summary["total_shortage"] == 0 else quarter_shortage["Q3"] / summary["total_shortage"]
summary["resilience_score"] = (
    0.45 * summary["urban_service_ratio"]
    + 0.25 * summary["ag_service_ratio"]
    + 0.15 * summary["eco_compliance_ratio"]
    + 0.15 * (1 - summary["buffer_months"] / 12)
)
if summary["resilience_score"] >= 0.82:
    summary["scenario"] = "Stable"
elif summary["resilience_score"] >= 0.60:
    summary["scenario"] = "Managed Stress"
else:
    summary["scenario"] = "Severe Stress"

hydro_rows = [["Month", "Inflow_MCM", "Evaporation_Loss_MCM"]]
for row in hydrology:
    hydro_rows.append([row["Month"], float(row["Inflow_MCM"]), float(row["Evaporation_Loss_MCM"])])

demand_rows = [["Month", "Urban_Demand_MCM", "Agriculture_Demand_MCM", "Eco_Min_Release_MCM"]]
for row in demand:
    demand_rows.append(
        [
            row["Month"],
            float(row["Urban_Demand_MCM"]),
            float(row["Agriculture_Demand_MCM"]),
            float(row["Eco_Min_Release_MCM"]),
        ]
    )

policy_rows = [["Parameter", "Value"]]
for name, value in POLICY:
    policy_rows.append([name, value])

balance_headers = [
    "Month",
    "Inflow_MCM",
    "Evaporation_Loss_MCM",
    "Urban_Demand_MCM",
    "Agriculture_Demand_MCM",
    "Eco_Min_Release_MCM",
    "Start_Storage_MCM",
    "Trigger_State",
    "Urban_Target_MCM",
    "Agriculture_Target_MCM",
    "Emergency_Buffer_Used_MCM",
    "Planned_Release_MCM",
    "Base_Usable_Water_MCM",
    "Feasible_Release_MCM",
    "Eco_Actual_MCM",
    "Urban_Actual_MCM",
    "Agriculture_Actual_MCM",
    "Urban_Shortage_MCM",
    "Agriculture_Shortage_MCM",
    "Eco_Shortage_MCM",
    "Total_Shortage_MCM",
    "End_Storage_MCM",
]

balance_rows = [balance_headers]
for item in monthly_rows:
    r = item["row"]
    month_formula = f"Hydrology_Input!A{r}"
    inflow_formula = f"Hydrology_Input!B{r}"
    evap_formula = f"Hydrology_Input!C{r}"
    urban_formula = f"Demand_Input!B{r}"
    ag_formula = f"Demand_Input!C{r}"
    eco_formula = f"Demand_Input!D{r}"
    if r == 2:
        start_formula = "Policy!$B$2"
    else:
        start_formula = f"V{r-1}"
    trigger_formula = (
        f'IF(G{r}<Policy!$B$7,"Emergency",IF(G{r}<Policy!$B$6,"Watch","Normal"))'
    )
    urban_target_formula = (
        f'=D{r}*IF(H{r}="Normal",1,IF(H{r}="Watch",Policy!$B$8,Policy!$B$9))'
    )[1:]
    ag_target_formula = (
        f'=E{r}*IF(H{r}="Normal",1,IF(H{r}="Watch",Policy!$B$10,Policy!$B$11))'
    )[1:]
    planned_formula = f"F{r}+I{r}+J{r}"
    base_formula = f"MAX(G{r}+B{r}-C{r}-Policy!$B$4,0)"
    emergency_formula = (
        f'IF(H{r}="Emergency",MIN(Policy!$B$12,MAX(0,L{r}-M{r}),'
        f'MAX(0,MAX(G{r}+B{r}-C{r}-Policy!$B$5,0)-M{r})),0)'
    )
    feasible_formula = f"MIN(L{r},M{r}+K{r})"
    eco_actual_formula = f"MIN(F{r},N{r})"
    urban_actual_formula = f"MIN(I{r},MAX(N{r}-O{r},0))"
    ag_actual_formula = f"MIN(J{r},MAX(N{r}-O{r}-P{r},0))"
    urban_short_formula = f"D{r}-P{r}"
    ag_short_formula = f"E{r}-Q{r}"
    eco_short_formula = f"F{r}-O{r}"
    total_short_formula = f"SUM(R{r}:T{r})"
    end_formula = f"MIN(Policy!$B$3,G{r}+B{r}-C{r}-O{r}-P{r}-Q{r})"

    balance_rows.append(
        [
            {"formula": month_formula, "value": item["month"], "type": "str"},
            {"formula": inflow_formula, "value": item["inflow"]},
            {"formula": evap_formula, "value": item["evap"]},
            {"formula": urban_formula, "value": item["urban_demand"]},
            {"formula": ag_formula, "value": item["ag_demand"]},
            {"formula": eco_formula, "value": item["eco_demand"]},
            {"formula": start_formula, "value": item["start_storage"]},
            {"formula": trigger_formula, "value": item["trigger_state"], "type": "str"},
            {"formula": urban_target_formula, "value": item["urban_target"]},
            {"formula": ag_target_formula, "value": item["ag_target"]},
            {"formula": emergency_formula, "value": item["emergency_used"]},
            {"formula": planned_formula, "value": item["planned_release"]},
            {"formula": base_formula, "value": item["base_usable"]},
            {"formula": feasible_formula, "value": item["feasible_release"]},
            {"formula": eco_actual_formula, "value": item["eco_actual"]},
            {"formula": urban_actual_formula, "value": item["urban_actual"]},
            {"formula": ag_actual_formula, "value": item["ag_actual"]},
            {"formula": urban_short_formula, "value": item["urban_shortage"]},
            {"formula": ag_short_formula, "value": item["ag_shortage"]},
            {"formula": eco_short_formula, "value": item["eco_shortage"]},
            {"formula": total_short_formula, "value": item["total_shortage"]},
            {"formula": end_formula, "value": item["end_storage"]},
        ]
    )

summary_rows = [
    ["Metric", "Value", None, "Quarter", "Shortage_MCM"],
    ["Total Inflow", {"formula": "SUM(Monthly_Balance!B2:B13)", "value": summary["total_inflow"]}, None, "Q1", {"formula": "SUM(Monthly_Balance!U2:U4)", "value": quarter_shortage["Q1"]}],
    ["Total Urban Demand", {"formula": "SUM(Monthly_Balance!D2:D13)", "value": summary["total_urban_demand"]}, None, "Q2", {"formula": "SUM(Monthly_Balance!U5:U7)", "value": quarter_shortage["Q2"]}],
    ["Total Agriculture Demand", {"formula": "SUM(Monthly_Balance!E2:E13)", "value": summary["total_ag_demand"]}, None, "Q3", {"formula": "SUM(Monthly_Balance!U8:U10)", "value": quarter_shortage["Q3"]}],
    ["Total Ecological Target", {"formula": "SUM(Monthly_Balance!F2:F13)", "value": summary["total_eco_demand"]}, None, "Q4", {"formula": "SUM(Monthly_Balance!U11:U13)", "value": quarter_shortage["Q4"]}],
    ["Total Urban Delivered", {"formula": "SUM(Monthly_Balance!P2:P13)", "value": summary["total_urban_actual"]}],
    ["Total Agriculture Delivered", {"formula": "SUM(Monthly_Balance!Q2:Q13)", "value": summary["total_ag_actual"]}],
    ["Total Ecological Delivered", {"formula": "SUM(Monthly_Balance!O2:O13)", "value": summary["total_eco_actual"]}],
    ["Urban Service Ratio", {"formula": "IF(B3=0,0,B6/B3)", "value": summary["urban_service_ratio"]}],
    ["Agriculture Service Ratio", {"formula": "IF(B4=0,0,B7/B4)", "value": summary["ag_service_ratio"]}],
    ["Ecological Compliance Ratio", {"formula": "IF(B5=0,0,B8/B5)", "value": summary["eco_compliance_ratio"]}],
    ["Total Shortage", {"formula": "SUM(Monthly_Balance!U2:U13)", "value": summary["total_shortage"]}],
    ["Watch Months", {"formula": 'COUNTIF(Monthly_Balance!H2:H13,"Watch")', "value": summary["watch_months"]}],
    ["Emergency Months", {"formula": 'COUNTIF(Monthly_Balance!H2:H13,"Emergency")', "value": summary["emergency_months"]}],
    ["Emergency Buffer Months", {"formula": 'COUNTIF(Monthly_Balance!K2:K13,\">0\")', "value": summary["buffer_months"]}],
    ["Minimum End Storage", {"formula": "MIN(Monthly_Balance!V2:V13)", "value": summary["min_end_storage"]}],
    ["End-of-Year Storage", {"formula": "Monthly_Balance!V13", "value": summary["end_storage"]}],
    ["End Storage Gap vs Target", {"formula": "B17-Policy!$B$13", "value": summary["end_gap"]}],
    ["Q3 Shortage Share", {"formula": "IF(B12=0,0,E4/B12)", "value": summary["q3_share"]}],
    ["Resilience Score", {"formula": "0.45*B9+0.25*B10+0.15*B11+0.15*(1-B15/12)", "value": summary["resilience_score"]}],
    ["Operating Scenario", {"formula": 'IF(B20>=0.82,\"Stable\",IF(B20>=0.60,\"Managed Stress\",\"Severe Stress\"))', "value": summary["scenario"], "type": "str"}],
]

sheets = [
    ("Hydrology_Input", hydro_rows),
    ("Demand_Input", demand_rows),
    ("Policy", policy_rows),
    ("Monthly_Balance", balance_rows),
    ("Scenario_Summary", summary_rows),
]

content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/worksheets/sheet3.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/worksheets/sheet4.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/worksheets/sheet5.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>
"""

rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>
"""

sheet_entries = "".join(
    f'<sheet name="{escape(name)}" sheetId="{idx}" r:id="rId{idx}"/>'
    for idx, (name, _) in enumerate(sheets, start=1)
)
workbook = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
    '<bookViews><workbookView xWindow="0" yWindow="0" windowWidth="24000" windowHeight="12000"/></bookViews>'
    f"<sheets>{sheet_entries}</sheets>"
    '<calcPr calcId="191029" fullCalcOnLoad="1"/>'
    "</workbook>"
)
workbook_rels = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    + "".join(
        f'<Relationship Id="rId{idx}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{idx}.xml"/>'
        for idx in range(1, 6)
    )
    + '<Relationship Id="rId6" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
    + "</Relationships>"
)
styles = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="1"><font><sz val="11"/><name val="Calibri"/><family val="2"/></font></fonts>
  <fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills>
  <borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs>
  <cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>
"""
core = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:creator>OpenAI Codex</dc:creator>
  <cp:lastModifiedBy>OpenAI Codex</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">2026-03-25T00:00:00Z</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">2026-03-25T00:00:00Z</dcterms:modified>
</cp:coreProperties>
"""
app = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>Codex</Application>
</Properties>
"""

with ZipFile(OUTPUT, "w", ZIP_DEFLATED) as zf:
    zf.writestr("[Content_Types].xml", content_types)
    zf.writestr("_rels/.rels", rels)
    zf.writestr("xl/workbook.xml", workbook)
    zf.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
    zf.writestr("xl/styles.xml", styles)
    zf.writestr("docProps/core.xml", core)
    zf.writestr("docProps/app.xml", app)
    for idx, (_, rows) in enumerate(sheets, start=1):
        zf.writestr(f"xl/worksheets/sheet{idx}.xml", sheet_xml(rows))
PY
