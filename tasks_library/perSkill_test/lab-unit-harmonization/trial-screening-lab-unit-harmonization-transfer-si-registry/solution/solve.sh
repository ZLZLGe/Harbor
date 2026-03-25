#!/bin/bash
set -euo pipefail

cd /root

python3 - <<'PY'
import pandas as pd

INPUT_FILE = "/root/environment/data/trial_screening_site_labs.csv"
SPEC_FILE = "/root/environment/data/registry_lab_spec.csv"
OUTPUT_FILE = "/root/trial_screening_labs_si.csv"

AMBIGUOUS_UNITS = {"site_default", "legacy_panel"}
OUTPUT_COLUMNS = [
    "study_id",
    "country_code",
    "site_code",
    "subject_id",
    "screening_visit",
    "collection_date",
    "specimen_id",
    "registry_test_code",
    "registry_test_name",
    "standard_value",
    "standard_unit",
]


def parse_value(raw_value):
    if pd.isna(raw_value):
        return None
    text = str(raw_value).strip()
    if not text:
        return None
    if "," in text:
        text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def split_aliases(alias_string):
    return {part.strip().lower() for part in str(alias_string).split("|") if part.strip()}


labs = pd.read_csv(INPUT_FILE, dtype=str, keep_default_na=False)
spec = pd.read_csv(SPEC_FILE, dtype=str, keep_default_na=False)

spec["si_min"] = spec["si_min"].astype(float)
spec["si_max"] = spec["si_max"].astype(float)
spec["conventional_to_si_factor"] = spec["conventional_to_si_factor"].astype(float)
spec["target_aliases"] = spec["target_unit_aliases"].apply(split_aliases)
spec["conventional_aliases"] = spec["conventional_unit_aliases"].apply(split_aliases)

spec_map = {row["analyte_code"]: row for _, row in spec.iterrows()}

labs = labs[labs["result_status"] == "FINAL"].copy()
labs = labs[labs["analyte_code"].isin(spec_map)].copy()

rows = []
for _, row in labs.iterrows():
    raw_value = parse_value(row["result_raw"])
    if raw_value is None:
        continue

    rule = spec_map[row["analyte_code"]]
    reported_unit = str(row["reported_unit"]).strip().lower()
    si_min = float(rule["si_min"])
    si_max = float(rule["si_max"])
    factor = float(rule["conventional_to_si_factor"])

    standardized = None
    if reported_unit in rule["target_aliases"]:
        standardized = raw_value
    elif reported_unit in rule["conventional_aliases"]:
        standardized = raw_value * factor
    elif reported_unit in AMBIGUOUS_UNITS:
        if si_min <= raw_value <= si_max:
            standardized = raw_value
        else:
            converted = raw_value * factor
            if si_min <= converted <= si_max:
                standardized = converted
    if standardized is None:
        continue
    if not (si_min <= standardized <= si_max):
        continue

    rows.append(
        {
            "study_id": row["study_id"],
            "country_code": row["country_code"],
            "site_code": row["site_code"],
            "subject_id": row["subject_id"],
            "screening_visit": row["screening_visit"],
            "collection_date": row["collection_date"],
            "specimen_id": row["specimen_id"],
            "registry_test_code": row["analyte_code"],
            "registry_test_name": rule["registry_test_name"],
            "standard_value": f"{standardized:.2f}",
            "standard_unit": rule["target_unit"],
        }
    )

output = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
output = output.sort_values(
    by=["collection_date", "site_code", "subject_id", "specimen_id"],
    kind="mergesort",
).reset_index(drop=True)
output.to_csv(OUTPUT_FILE, index=False)
PY
