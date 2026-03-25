#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import csv
import json
from pathlib import Path

INPUT_STREAM = Path("/root/environment/data/ed_alert_stream.jsonl")
REFERENCE_FILE = Path("/root/environment/data/critical_test_reference.csv")
OUTPUT_FILE = Path("/root/ed_alert_lab_reconciliation.json")

CRITICAL_FIELDS = ["record_id", "encounter_id", "test_code", "arrival_time", "result_raw"]

TEST_CONFIG = {
    "K": {
        "equivalent_units": {"mEq/L", "mmol/L"},
        "alt_conversions": [],
    },
    "GLU": {
        "equivalent_units": {"mg/dL"},
        "alt_conversions": [("mmol/L", 1.0 / 0.0555)],
    },
    "CREA": {
        "equivalent_units": {"mg/dL"},
        "alt_conversions": [("umol/L", 1.0 / 88.4)],
    },
    "HGB": {
        "equivalent_units": {"g/dL"},
        "alt_conversions": [("g/L", 0.1)],
    },
    "LAC": {
        "equivalent_units": {"mmol/L"},
        "alt_conversions": [("mg/dL", 1.0 / 9.01)],
    },
    "CA": {
        "equivalent_units": {"mg/dL"},
        "alt_conversions": [("mmol/L", 4.0)],
    },
}


def parse_value(raw_value: str):
    text = str(raw_value).strip()
    if text == "":
        return None
    text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def format_value(value: float) -> str:
    return f"{value:.2f}"


def is_in_range(value: float, lower: float, upper: float) -> bool:
    return lower <= value <= upper


def normalize_unit(value: float, reported_unit: str, test_code: str, lower: float, upper: float):
    config = TEST_CONFIG[test_code]
    unit = (reported_unit or "").strip()
    if unit in config["equivalent_units"]:
        return value, False

    for expected_unit, factor in config["alt_conversions"]:
        if unit == expected_unit:
            return value * factor, True

    if unit == "ed_default":
        if is_in_range(value, lower, upper):
            return value, False
        for _expected_unit, factor in config["alt_conversions"]:
            candidate = value * factor
            if is_in_range(candidate, lower, upper):
                return candidate, True

    return value, False


reference_rows = []
with REFERENCE_FILE.open(newline="", encoding="utf-8") as handle:
    reader = csv.DictReader(handle)
    for row in reader:
        row["display_order"] = int(row["display_order"])
        row["target_min"] = float(row["target_min"])
        row["target_max"] = float(row["target_max"])
        reference_rows.append(row)

reference_by_code = {row["test_code"]: row for row in reference_rows}

encounters = {}


def get_or_create_encounter(encounter_id: str, patient_id: str, arrival_time: str):
    encounter = encounters.get(encounter_id)
    if encounter is None:
        encounter = {
            "encounter_id": encounter_id,
            "patient_id": patient_id,
            "arrival_time": arrival_time,
            "standardized_results": [],
            "excluded_records": [],
        }
        encounters[encounter_id] = encounter
    else:
        if not encounter["patient_id"] and patient_id:
            encounter["patient_id"] = patient_id
        if not encounter["arrival_time"] and arrival_time:
            encounter["arrival_time"] = arrival_time
    return encounter


with INPUT_STREAM.open(encoding="utf-8") as handle:
    for line in handle:
        if not line.strip():
            continue
        row = json.loads(line)
        test_code = row.get("test_code", "")
        if test_code not in reference_by_code:
            continue

        encounter_id = (row.get("encounter_id") or "").strip()
        if not encounter_id:
            continue

        patient_id = (row.get("patient_id") or "").strip()
        arrival_time = (row.get("arrival_time") or "").strip()
        encounter = get_or_create_encounter(encounter_id, patient_id, arrival_time)

        missing_field = None
        for field_name in CRITICAL_FIELDS:
            if str(row.get(field_name, "")).strip() == "":
                missing_field = field_name
                break

        if missing_field is not None:
            encounter["excluded_records"].append(
                {
                    "record_id": (row.get("record_id") or "").strip(),
                    "test_code": test_code,
                    "reason": f"missing_{missing_field}",
                }
            )
            continue

        ref = reference_by_code[test_code]
        parsed_value = parse_value(row["result_raw"])
        if parsed_value is None:
            continue

        normalized_value, converted = normalize_unit(
            parsed_value,
            row.get("reported_unit", ""),
            test_code,
            ref["target_min"],
            ref["target_max"],
        )

        encounter["standardized_results"].append(
            {
                "record_id": row["record_id"].strip(),
                "test_code": test_code,
                "standard_name": ref["standard_name"],
                "standard_value": format_value(normalized_value),
                "standard_unit": ref["target_unit"],
                "converted": converted,
            }
        )

report = {
    "report_id": "ed-critical-lab-reconciliation",
    "target_tests": [
        {
            "test_code": row["test_code"],
            "standard_name": row["standard_name"],
            "standard_unit": row["target_unit"],
        }
        for row in sorted(reference_rows, key=lambda item: item["display_order"])
    ],
    "encounters": [],
}


def result_sort_key(item):
    return (reference_by_code[item["test_code"]]["display_order"], item["record_id"])


for encounter in sorted(encounters.values(), key=lambda item: (item["arrival_time"], item["encounter_id"])):
    encounter["standardized_results"] = sorted(encounter["standardized_results"], key=result_sort_key)
    encounter["excluded_records"] = sorted(encounter["excluded_records"], key=lambda item: item["record_id"])
    encounter["had_unit_conversion"] = any(item["converted"] for item in encounter["standardized_results"])
    report["encounters"].append(
        {
            "encounter_id": encounter["encounter_id"],
            "patient_id": encounter["patient_id"],
            "arrival_time": encounter["arrival_time"],
            "had_unit_conversion": encounter["had_unit_conversion"],
            "standardized_results": encounter["standardized_results"],
            "excluded_records": encounter["excluded_records"],
        }
    )

OUTPUT_FILE.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
PY
