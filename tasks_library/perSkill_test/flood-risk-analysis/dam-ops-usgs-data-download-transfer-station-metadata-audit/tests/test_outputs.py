import csv
import json
import math
import os

import pandas as pd
from dataretrieval import nwis


INPUT_PATH = "/root/data/dam_watch_station_candidates.tsv"
OUTPUT_PATH = "/root/output/station_metadata_audit.json"
EXPECTED_KEYS = {
    "station_id",
    "site_name",
    "state",
    "latitude",
    "longitude",
    "drainage_area_sqmi",
}


def load_candidates() -> list[dict[str, str]]:
    with open(INPUT_PATH, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        return list(reader)


def column_name(df: pd.DataFrame, candidates: list[str], label: str) -> str:
    lower_to_original = {str(col).lower(): col for col in df.columns}
    for candidate in candidates:
        if candidate in lower_to_original:
            return lower_to_original[candidate]
    raise AssertionError(f"Unable to find {label} column in site metadata: {list(df.columns)}")


def missing(value) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return str(value).strip() == ""


def clean_state(value) -> str:
    text = str(value).strip()
    return text[:-2] if text.endswith(".0") else text


def compute_expected_rows():
    rows = []
    for candidate in load_candidates():
        station_id = candidate["station_id"]
        try:
            info, _ = nwis.get_info(sites=station_id)
        except Exception:
            continue

        if info.empty:
            continue

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
        if not str(row[site_type_col]).strip().upper().startswith("ST"):
            continue

        required_values = [
            row[site_name_col],
            row[state_col],
            row[lat_col],
            row[lon_col],
            row[drainage_col],
        ]
        if any(missing(value) for value in required_values):
            continue

        rows.append(
            {
                "station_id": station_id,
                "site_name": str(row[site_name_col]).strip(),
                "state": clean_state(row[state_col]),
                "latitude": round(float(row[lat_col]), 6),
                "longitude": round(float(row[lon_col]), 6),
                "drainage_area_sqmi": round(float(row[drainage_col]), 3),
            }
        )

    rows.sort(key=lambda item: (item["state"], item["station_id"]))
    return rows


def load_output_rows():
    with open(OUTPUT_PATH, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    assert isinstance(payload, list), "Output must be a JSON array"
    return payload


def test_output_exists():
    assert os.path.exists(OUTPUT_PATH), "JSON file not found at /root/output/station_metadata_audit.json"


def test_output_schema():
    rows = load_output_rows()
    for row in rows:
        assert set(row.keys()) == EXPECTED_KEYS
        assert isinstance(row["station_id"], str)
        assert isinstance(row["site_name"], str)
        assert isinstance(row["state"], str)
        assert isinstance(row["latitude"], (int, float))
        assert isinstance(row["longitude"], (int, float))
        assert isinstance(row["drainage_area_sqmi"], (int, float))


def test_output_matches_expected_rows():
    assert load_output_rows() == compute_expected_rows()
