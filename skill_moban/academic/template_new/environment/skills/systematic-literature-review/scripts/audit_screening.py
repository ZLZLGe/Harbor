#!/usr/bin/env python3
import csv
import json
import os
from pathlib import Path

from _catalog import load_records
from _record_logic import canonical_row, eligibility_reason, is_eligible
WORKSPACE_ROOT = Path(os.environ.get("WORKSPACE_ROOT", "/app/workspace"))
CANDIDATES_PATH = WORKSPACE_ROOT / "data" / "candidate_records.csv"
CSV_PATH = WORKSPACE_ROOT / "included_studies.csv"


with CANDIDATES_PATH.open("r", encoding="utf-8", newline="") as handle:
    candidate_ids = [row["study_id"] for row in csv.DictReader(handle)]

with CSV_PATH.open("r", encoding="utf-8", newline="") as handle:
    current_rows = list(csv.DictReader(handle))

records = load_records(candidate_ids)
recommended_rows = [canonical_row(record) for study_id, record in records.items() if is_eligible(record)]
recommended_by_id = {row["study_id"]: row for row in recommended_rows}
current_by_id = {row["study_id"]: {key: (value or "").strip() for key, value in row.items()} for row in current_rows}

missing_from_included = sorted(set(recommended_by_id) - set(current_by_id))
remove_from_included = sorted(set(current_by_id) - set(recommended_by_id))
field_repairs: dict[str, dict[str, str]] = {}

for study_id, expected in recommended_by_id.items():
    observed = current_by_id.get(study_id)
    if not observed:
        continue
    mismatches = {}
    for field, expected_value in expected.items():
        observed_value = observed.get(field, "")
        if expected_value != observed_value:
            mismatches[field] = expected_value
    if mismatches:
        field_repairs[study_id] = mismatches

exclusion_notes = {
    study_id: eligibility_reason(record)
    for study_id, record in records.items()
    if not is_eligible(record)
}

print(
    json.dumps(
        {
            "eligible_study_ids": sorted(recommended_by_id),
            "missing_from_included": missing_from_included,
            "remove_from_included": remove_from_included,
            "field_repairs": field_repairs,
            "suggested_rows": recommended_rows,
            "excluded_candidate_reasons": exclusion_notes,
        },
        indent=2,
        ensure_ascii=False,
    )
)
