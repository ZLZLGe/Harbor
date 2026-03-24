#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
import os
import re
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET

import pandas as pd


DATA_DIR = Path(os.getenv("DATA_DIR", "/root/data"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "/root/output"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HIERARCHY_COLS = [f"unified_issue_l{i}" for i in range(1, 5)]

TAXONOMY = {
    "graffiti": ["exterior | upkeep", "surface | cleanup", "graffiti | removal", "wall | marking"],
    "trip_hazard": ["exterior | upkeep", "walkway | repair", "surface | hazard", "trip | hazard"],
    "tree_branch": ["exterior | upkeep", "canopy | trimming", "branch | obstruction", "route | clearance"],
    "bulk_dumping": ["grounds | sanitation", "waste | removal", "bulky | debris", "dumping | pickup"],
    "pest": ["grounds | sanitation", "pest | control", "rodent | activity", "inspection | bait"],
    "recycling_overflow": ["grounds | sanitation", "recycling | reset", "container | overflow", "bin | clearance"],
    "elevator": ["access | mobility", "vertical | transport", "elevator | outage", "car | stalled"],
    "auto_door": ["access | mobility", "entry | systems", "automatic | door", "opener | fault"],
    "gate": ["access | mobility", "entry | systems", "vehicle | gate", "barrier | fault"],
    "water_leak": ["plumbing | utility", "pipe | leak", "active | water", "ceiling | drip"],
    "hot_water": ["plumbing | utility", "domestic | heating", "hot | water", "supply | loss"],
    "drain_backup": ["plumbing | utility", "drain | waste", "backup | blockage", "fixture | overflow"],
    "no_cooling": ["climate | comfort", "air | circulation", "cooling | outage", "warm | space"],
    "no_heat": ["climate | comfort", "boiler | service", "heat | outage", "cold | space"],
    "exterior_lighting": ["power | lighting", "outdoor | fixtures", "light | outage", "dark | area"],
}

CHANNEL_MAP = {
    "311 phone": "phone",
    "call center": "phone",
    "phone desk": "phone",
    "web form": "web",
    "self-service": "web",
    "nyc app": "mobile_app",
    "email": "email",
    "resident portal": "resident_portal",
    "front desk": "front_desk",
}

PRIORITY_MAP = {
    "emergency": "emergency",
    "life_safety": "emergency",
    "p1": "emergency",
    "urgent": "urgent",
    "same_day": "urgent",
    "p2": "urgent",
    "routine": "routine",
    "planned": "routine",
    "p3": "routine",
}


def read_simple_xlsx(path: Path) -> pd.DataFrame:
    ns = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with ZipFile(path) as zf:
        worksheet = ET.fromstring(zf.read("xl/worksheets/sheet1.xml"))
    rows = []
    for row in worksheet.findall(".//a:sheetData/a:row", ns):
        values = []
        for cell in row.findall("a:c", ns):
            cell_type = cell.attrib.get("t")
            if cell_type == "inlineStr":
                node = cell.find("a:is/a:t", ns)
                values.append(node.text if node is not None else "")
            else:
                node = cell.find("a:v", ns)
                values.append(node.text if node is not None else "")
        rows.append(values)
    headers = rows[0]
    data = rows[1:]
    return pd.DataFrame(data, columns=headers)


def standardize_delimiter(text: str) -> str:
    text = str(text).strip()
    for delimiter in [" / ", " :: ", " -> "]:
        text = text.replace(delimiter, " > ")
    return " > ".join(part.strip() for part in text.split(" > "))


def normalize_issue_text(text: str) -> str:
    text = standardize_delimiter(text).lower()
    replacements = {
        "&": " and ",
        "-": " ",
        "hallway wall": "wall marking",
        "wall markings": "wall marking",
        "tree limbs": "tree branch",
        "low branches": "tree branch",
        "abandoned items": "bulky debris",
        "dumped furniture": "bulky debris",
        "illegal dumping": "bulky debris",
        "mouse activity": "rodent activity",
        "rat sighting": "rodent activity",
        "rodent sighting": "rodent activity",
        "recycling cage": "recycling container",
        "container full": "container overflow",
        "stalled car": "car stalled",
        "lift service": "elevator service",
        "lift outage": "elevator outage",
        "elevator offline": "elevator outage",
        "auto operators": "automatic door",
        "automatic opener": "automatic door",
        "door opener fault": "opener fault",
        "operator failure": "opener fault",
        "gate arm": "vehicle gate",
        "roll gate": "vehicle gate",
        "resident gate": "vehicle gate",
        "water leaks": "water leak",
        "active water": "active leak",
        "pipe break": "active leak",
        "burst pipe": "active leak",
        "hot water loss": "no hot water",
        "air conditioner failure": "cooling outage",
        "air conditioning": "cooling",
        "condenser fault": "cooling outage",
        "compressor fault": "cooling outage",
        "streetlight outage": "light outage",
        "pathway lights": "light outage",
        "parking lot fixtures": "outdoor light",
        "dark block": "dark area",
        "dark zone": "dark area",
        "warm apartment": "warm space",
        "warm room": "warm space",
        "warm unit": "warm space",
        "hot apartment": "warm space",
        "hot lecture hall": "warm space",
        "cold apartment": "cold space",
        "cold classroom": "cold space",
        "cold unit": "cold space",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r"[^a-z0-9> ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    parts = [part.strip() for part in text.split(">")]
    return " > ".join(parts)


def infer_issue_key(normalized_path: str) -> str:
    text = normalized_path
    if "graffiti" in text:
        return "graffiti"
    if "trip hazard" in text:
        return "trip_hazard"
    if "tree branch" in text or ("branch obstruction" in text):
        return "tree_branch"
    if "bulky debris" in text or "bulk pickup" in text or "bulk removal" in text:
        return "bulk_dumping"
    if "rodent activity" in text or "rodents" in text:
        return "pest"
    if "recycling" in text and ("overflow" in text or "container" in text):
        return "recycling_overflow"
    if "elevator" in text and ("stalled" in text or "outage" in text or "stuck" in text):
        return "elevator"
    if "automatic door" in text or "opener fault" in text:
        return "auto_door"
    if "vehicle gate" in text or "gate malfunction" in text or "entry gate fault" in text:
        return "gate"
    if "no hot water" in text or "hot water" in text:
        return "hot_water"
    if "drain" in text or "toilet overflow" in text or "backup" in text or "blockage" in text:
        return "drain_backup"
    if "cooling outage" in text or "no cooling" in text or "warm space" in text:
        return "no_cooling"
    if "no heat" in text or "heat outage" in text or "cold space" in text:
        return "no_heat"
    if "light outage" in text or "dark area" in text:
        return "exterior_lighting"
    if "active leak" in text or "ceiling drip" in text or "hallway drip" in text:
        return "water_leak"
    raise ValueError(f"Unrecognized issue path: {normalized_path}")


def load_city() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "city311_service_requests.csv")
    return pd.DataFrame(
        {
            "source_system": "city311",
            "request_id": df["sr_id"],
            "raw_issue_path": df["complaint_hierarchy"],
            "raw_channel": df["submission_channel"],
            "raw_priority": df["priority_code"],
            "sla_target_hours": df["sla_target_hours"].astype(int),
        }
    )


def load_campus() -> pd.DataFrame:
    rows = []
    with open(DATA_DIR / "campus_maintenance_queue.jsonl", "r", encoding="utf-8") as handle:
        for line in handle:
            rows.append(json.loads(line))
    df = pd.DataFrame(rows)
    return pd.DataFrame(
        {
            "source_system": "campus_facilities",
            "request_id": df["ticket_ref"],
            "raw_issue_path": df["issue_tree"],
            "raw_channel": df["request_channel"],
            "raw_priority": df["urgency_code"],
            "sla_target_hours": df["target_hours"].astype(int),
        }
    )


def load_property() -> pd.DataFrame:
    df = read_simple_xlsx(DATA_DIR / "residential_portfolio_work_orders.xlsx")
    return pd.DataFrame(
        {
            "source_system": "property_management",
            "request_id": df["work_order_no"],
            "raw_issue_path": df["problem_path"],
            "raw_channel": df["resident_touchpoint"],
            "raw_priority": df["service_level"],
            "sla_target_hours": df["due_within_hours"].astype(int),
        }
    )


df = pd.concat([load_city(), load_campus(), load_property()], ignore_index=True)
df["source_issue_path"] = df["raw_issue_path"].map(standardize_delimiter)
df["normalized_issue_path"] = df["source_issue_path"].map(normalize_issue_text)
df["source_depth"] = df["source_issue_path"].str.count(" > ") + 1
df["intake_channel"] = df["raw_channel"].str.lower().map(CHANNEL_MAP)
df["priority_band"] = df["raw_priority"].astype(str).map(lambda value: PRIORITY_MAP[value.lower()])
df["issue_key"] = df["normalized_issue_path"].map(infer_issue_key)

for index, column in enumerate(HIERARCHY_COLS):
    df[column] = df["issue_key"].map(lambda key, i=index: TAXONOMY[key][i])

crosswalk = df[
    [
        "source_system",
        "request_id",
        "source_issue_path",
        "normalized_issue_path",
        "source_depth",
        "intake_channel",
        "priority_band",
        "sla_target_hours",
        *HIERARCHY_COLS,
    ]
].sort_values(["source_system", "request_id"]).reset_index(drop=True)

hierarchy = crosswalk[HIERARCHY_COLS].drop_duplicates().sort_values(HIERARCHY_COLS).reset_index(drop=True)

rollup = (
    crosswalk.groupby(HIERARCHY_COLS, as_index=False)
    .agg(
        request_count=("request_id", "count"),
        source_system_count=("source_system", "nunique"),
        intake_channel_count=("intake_channel", "nunique"),
        emergency_count=("priority_band", lambda s: int((s == "emergency").sum())),
        urgent_count=("priority_band", lambda s: int((s == "urgent").sum())),
        routine_count=("priority_band", lambda s: int((s == "routine").sum())),
        median_sla_target_hours=("sla_target_hours", "median"),
        max_sla_target_hours=("sla_target_hours", "max"),
    )
    .sort_values(HIERARCHY_COLS)
    .reset_index(drop=True)
)

crosswalk.to_csv(OUTPUT_DIR / "service_request_crosswalk.csv", index=False)
hierarchy.to_csv(OUTPUT_DIR / "service_request_taxonomy_hierarchy.csv", index=False)
rollup.to_csv(OUTPUT_DIR / "dispatch_sla_rollup.csv", index=False)
PY
