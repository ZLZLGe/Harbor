#!/bin/bash
set -euo pipefail

python3 <<'PY'
import csv
import json
import math
import os

import pandas as pd
from dataretrieval import nwis


INPUT_PATH = "/root/data/dam_watch_station_candidates.tsv"
OUTPUT_PATH = "/root/output/station_metadata_audit.json"


def load_candidates(path: str) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        return list(reader)


def column_name(df: pd.DataFrame, candidates: list[str], label: str) -> str:
    lower_to_original = {str(col).lower(): col for col in df.columns}
    for candidate in candidates:
        if candidate in lower_to_original:
            return lower_to_original[candidate]
    raise RuntimeError(f"Unable to find {label} column in site metadata: {list(df.columns)}")


def missing(value) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return str(value).strip() == ""


def clean_state(value) -> str:
    text = str(value).strip()
    return text[:-2] if text.endswith(".0") else text


def fetch_station_record(station_id: str) -> dict | None:
    try:
        info, _ = nwis.get_info(sites=station_id)
    except Exception:
        return None

    if info.empty:
        return None

    site_type_col = column_name(info, ["site_tp_cd", "site_type", "site_tp"], "site type")
    site_name_col = column_name(info, ["station_nm", "site_name", "site_nm"], "site name")
    state_col = column_name(info, ["state_cd", "state_alpha_cd", "state"], "state")
    lat_col = column_name(info, ["dec_lat_va", "latitude", "lat_va"], "latitude")
    lon_col = column_name(info, ["dec_long_va", "longitude", "long_va", "lon_va"], "longitude")
    drainage_col = column_name(
        info,
        ["drain_area_va", "drainage_area_va", "drain_area"],
        "drainage area",
    )

    row = info.iloc[0]
    site_type = str(row[site_type_col]).strip().upper()
    if not site_type.startswith("ST"):
        return None

    required_values = [
        row[site_name_col],
        row[state_col],
        row[lat_col],
        row[lon_col],
        row[drainage_col],
    ]
    if any(missing(value) for value in required_values):
        return None

    return {
        "station_id": station_id,
        "site_name": str(row[site_name_col]).strip(),
        "state": clean_state(row[state_col]),
        "latitude": round(float(row[lat_col]), 6),
        "longitude": round(float(row[lon_col]), 6),
        "drainage_area_sqmi": round(float(row[drainage_col]), 3),
    }


results = []
for candidate in load_candidates(INPUT_PATH):
    record = fetch_station_record(candidate["station_id"])
    if record is not None:
        results.append(record)

results.sort(key=lambda item: (item["state"], item["station_id"]))

os.makedirs("/root/output", exist_ok=True)
with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
    json.dump(results, handle, indent=2)
PY
