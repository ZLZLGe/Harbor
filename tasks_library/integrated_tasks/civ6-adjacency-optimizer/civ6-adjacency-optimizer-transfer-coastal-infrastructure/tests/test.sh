#!/bin/bash

pip3 install --break-system-packages pytest==8.3.4 pytest-json-ctrf==0.3.5 2>/dev/null || \
pip3 install pytest==8.3.4 pytest-json-ctrf==0.3.5 2>/dev/null || true

export PYTHONPATH="/tests:/tests/src:$PYTHONPATH"

mkdir -p /logs/verifier/scores
mkdir -p /logs/verifier/solutions

cp /output/coastal_corridor_plan.json /logs/verifier/solutions/ 2>/dev/null || true

pytest /tests/test_outputs.py -v --tb=short --ctrf /logs/verifier/ctrf.json > /logs/verifier/test_output.log 2>&1

cat /logs/verifier/test_output.log

python3 <<'EOF'
from pathlib import Path

score_file = Path("/logs/verifier/scores/coastal_corridor.txt")

if score_file.exists():
    try:
        score = float(score_file.read_text().strip())
        print(f"coastal_corridor: {score:.3f}")
    except ValueError:
        print("coastal_corridor: 0.000 (parse error)")
        score = 0.0
else:
    print("coastal_corridor: 0.000 (no score file)")
    score = 0.0

print(f"\\nFinal score: {score:.3f}")

with open("/logs/verifier/reward.txt", "w") as f:
    f.write(f"{score:.3f}")
EOF

exit 0
