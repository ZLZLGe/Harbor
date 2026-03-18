#!/bin/bash

LOG_ROOT="${LOG_ROOT:-/logs/verifier}"
TEST_SCRIPT_PATH="${TEST_SCRIPT_PATH:-/tests/test_outputs.py}"

mkdir -p "$LOG_ROOT/scores"
mkdir -p "$LOG_ROOT/solutions"

cp /output/festival_layout_plan.json "$LOG_ROOT/solutions/" 2>/dev/null || true

python3 "$TEST_SCRIPT_PATH" > "$LOG_ROOT/test_output.log" 2>&1

cat "$LOG_ROOT/test_output.log"

python3 <<'PY'
from pathlib import Path
import os

log_root = Path(os.environ.get("LOG_ROOT", "/logs/verifier"))
score_file = log_root / "scores" / "festival_layout_plan.txt"

if score_file.exists():
    try:
        score = float(score_file.read_text().strip())
    except ValueError:
        score = 0.0
else:
    score = 0.0

print(f"festival_layout_plan: {score:.3f}")
print(f"\nFinal score: {score:.3f}")

with open(log_root / "reward.txt", "w") as f:
    f.write(f"{score:.3f}")
PY
