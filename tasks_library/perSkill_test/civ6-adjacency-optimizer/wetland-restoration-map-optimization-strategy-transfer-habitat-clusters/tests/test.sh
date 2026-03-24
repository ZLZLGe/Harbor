#!/bin/bash

mkdir -p /logs/verifier/scores
mkdir -p /logs/verifier/solutions

cp /output/wetland_restoration_layout.json /logs/verifier/solutions/ 2>/dev/null || true

python3 /tests/test_outputs.py > /logs/verifier/test_output.log 2>&1
TEST_EXIT_CODE=$?

cat /logs/verifier/test_output.log

python3 <<'PY'
from pathlib import Path

score_path = Path("/logs/verifier/scores/wetland_restoration_layout.txt")
reward_path = Path("/logs/verifier/reward.txt")

score = 0.0
if score_path.exists():
    try:
        score = float(score_path.read_text().strip())
    except ValueError:
        score = 0.0

print(f"\nFinal score: {score:.3f}")
reward_path.write_text(f"{score:.3f}")
PY

exit "$TEST_EXIT_CODE"
