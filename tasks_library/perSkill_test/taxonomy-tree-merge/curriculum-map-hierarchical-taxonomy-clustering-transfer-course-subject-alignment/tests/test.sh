#!/bin/bash
set -euo pipefail

apt-get update
apt-get install -y curl

curl -LsSf https://astral.sh/uv/0.9.7/install.sh | sh
source "$HOME/.local/bin/env"

uvx \
  --with pytest==8.4.1 \
  --with pytest-json-ctrf==0.3.5 \
  --with pytest-json-report==1.5.0 \
  --with pandas==2.2.0 \
  pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA --json-report --json-report-file=/logs/verifier/report.json

python3 <<'PY'
import json

P0_TESTS = [
    "test_output_files_exist",
    "test_mapping_schema_and_row_count",
    "test_hierarchy_schema_and_uniqueness",
    "test_summary_schema_and_consistency",
    "test_university_coverage",
    "test_source_path_normalization",
    "test_top_level_subject_count",
    "test_fixed_four_level_structure",
    "test_taxonomy_naming_rules",
    "test_intro_programming_alignment",
]

P1_TESTS = [
    "test_calculus_alignment",
    "test_general_chemistry_alignment",
    "test_overlap_summary_strength",
    "test_hierarchy_matches_mapping",
]

P2_TESTS = [
    "test_equivalency_group_format",
    "test_credit_range_reasonable",
]

with open("/logs/verifier/report.json", "r", encoding="utf-8") as handle:
    report = json.load(handle)

passed = set()
for test in report.get("tests", []):
    if test.get("outcome") == "passed":
        passed.add(test.get("nodeid", "").split("::")[-1])

p0 = sum(name in passed for name in P0_TESTS)
p1 = sum(name in passed for name in P1_TESTS)
p2 = sum(name in passed for name in P2_TESTS)

score = (p0 / len(P0_TESTS) * 0.55) + (p1 / len(P1_TESTS) * 0.30) + (p2 / len(P2_TESTS) * 0.15)

with open("/logs/verifier/reward.txt", "w", encoding="utf-8") as handle:
    handle.write(f"{score:.4f}\n")
PY
