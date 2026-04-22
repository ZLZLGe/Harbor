#!/usr/bin/env python3
import csv
import json
import os
from pathlib import Path

import requests

from _catalog import load_records
from _record_logic import canonical_comparator_type, canonical_primary_outcome_direction, is_eligible
from _service_helper import ensure_service


API_BASE = os.environ.get("ACADEMIC_API_URL", "http://127.0.0.1:8123")
WORKSPACE_ROOT = Path(os.environ.get("WORKSPACE_ROOT", "/app/workspace"))
CANDIDATES_PATH = WORKSPACE_ROOT / "data" / "candidate_records.csv"
CSV_PATH = WORKSPACE_ROOT / "included_studies.csv"
SUMMARY_PATH = WORKSPACE_ROOT / "summary.md"


with CANDIDATES_PATH.open("r", encoding="utf-8", newline="") as handle:
    candidate_ids = [row["study_id"] for row in csv.DictReader(handle)]

with CSV_PATH.open("r", encoding="utf-8", newline="") as handle:
    current_included_ids = [row["study_id"] for row in csv.DictReader(handle)]

summary = SUMMARY_PATH.read_text(encoding="utf-8")

ensure_service()

candidate_records = list(load_records(candidate_ids).values())
target_records = [record for record in candidate_records if is_eligible(record)]
target_ids = [record["study_id"] for record in target_records]
response = requests.post(
    f"{API_BASE}/validate/summary",
    json={"summary": summary, "included_study_ids": target_ids},
    timeout=30,
)
response.raise_for_status()
payload = response.json()

passive_control_support = []
active_comparator_limits = []
for record in target_records:
    comparator_type = canonical_comparator_type(record)
    outcome_direction = canonical_primary_outcome_direction(record)
    evidence_note = record["outcome_note"]
    if outcome_direction == "benefit_vs_control":
        passive_control_support.append(
            {
                "study_id": record["study_id"],
                "short_citation": record["short_citation"],
                "comparator_type": comparator_type,
                "evidence_note": evidence_note,
            }
        )
    if outcome_direction == "similar_to_active_diet":
        active_comparator_limits.append(
            {
                "study_id": record["study_id"],
                "short_citation": record["short_citation"],
                "comparator_type": comparator_type,
                "evidence_note": evidence_note,
            }
        )

print(
    json.dumps(
        {
            "summary_validation": payload,
            "current_included_ids": current_included_ids,
            "target_study_ids": target_ids,
            "required_summary_points": [
                "Restrict scope to adults with diagnosed type 2 diabetes.",
                "State that four randomized studies remain in scope.",
                "Acknowledge glycaemic benefit relative to passive control conditions.",
                "State that superiority over active dietary comparators was not consistent.",
            ],
            "supporting_evidence": {
                "benefit_vs_passive_control": passive_control_support,
                "active_comparator_limits": active_comparator_limits,
            },
        },
        indent=2,
        ensure_ascii=False,
    )
)
