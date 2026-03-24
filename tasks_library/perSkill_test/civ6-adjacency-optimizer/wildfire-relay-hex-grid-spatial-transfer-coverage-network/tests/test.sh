#!/bin/bash

pip3 install --break-system-packages pytest==8.3.4 pytest-json-ctrf==0.3.5 2>/dev/null || \
pip3 install pytest==8.3.4 pytest-json-ctrf==0.3.5 2>/dev/null || true

mkdir -p /logs/verifier/scores
mkdir -p /logs/verifier/solutions

cp /output/wildfire_relay_plan.json /logs/verifier/solutions/ 2>/dev/null || true

pytest /tests/test_outputs.py -v --tb=short --ctrf /logs/verifier/ctrf.json > /logs/verifier/test_output.log 2>&1

cat /logs/verifier/test_output.log

python3 <<'PY'
from pathlib import Path

score_file = Path("/logs/verifier/scores/wildfire_relay.txt")

if score_file.exists():
    try:
        score = float(score_file.read_text().strip())
    except ValueError:
        score = 0.0
else:
    score = 0.0

print(f"wildfire_relay: {score:.3f}")
print(f"\\nFinal score: {score:.3f}")

Path("/logs/verifier/reward.txt").write_text(f"{score:.3f}")
PY

exit 0
