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
    "test_crosswalk_schema_and_row_count",
    "test_hierarchy_schema_and_uniqueness",
    "test_summary_schema_and_consistency",
    "test_source_system_coverage",
    "test_path_normalization",
    "test_top_level_service_count",
    "test_fixed_five_level_structure",
    "test_taxonomy_naming_rules",
    "test_summary_totals",
]

P1_TESTS = [
    "test_same_day_alignment",
    "test_prenatal_alignment",
    "test_knee_replacement_alignment",
    "test_behavioral_medication_alignment",
]

P2_TESTS = [
    "test_cross_source_mix",
    "test_hierarchy_matches_crosswalk",
]

with open("/logs/verifier/report.json", "r", encoding="utf-8") as handle:
    report = json.load(handle)

passed_tests = set()
for test in report.get("tests", []):
    if test.get("outcome") == "passed":
        passed_tests.add(test.get("nodeid", "").split("::")[-1])

p0_passed = sum(name in passed_tests for name in P0_TESTS)
p1_passed = sum(name in passed_tests for name in P1_TESTS)
p2_passed = sum(name in passed_tests for name in P2_TESTS)
score = (p0_passed / len(P0_TESTS) * 0.55) + (p1_passed / len(P1_TESTS) * 0.30) + (p2_passed / len(P2_TESTS) * 0.15)

with open("/logs/verifier/reward.txt", "w", encoding="utf-8") as handle:
    handle.write(f"{score:.4f}\n")
PY
