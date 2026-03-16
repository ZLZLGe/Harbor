#!/bin/bash
set -euo pipefail

TASK_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_FILE="/tests/test_outputs.py"
if [ ! -f "$TEST_FILE" ]; then
  TEST_FILE="$TASK_ROOT/tests/test_outputs.py"
fi

LOG_ROOT="/logs/verifier"
if ! mkdir -p "$LOG_ROOT/scores" 2>/dev/null; then
  LOG_ROOT="$TASK_ROOT/.logs/verifier"
  mkdir -p "$LOG_ROOT/scores"
fi

export SCORE_DIR="$LOG_ROOT/scores"
export DATA_FILE="${DATA_FILE:-/data/puzzle_map_calibration/scenario.json}"
export OUTPUT_DIR="${OUTPUT_DIR:-/output}"

python3 "$TEST_FILE" > "$LOG_ROOT/test_output.log" 2>&1

cat "$LOG_ROOT/test_output.log"

python3 <<'PY'
import os
from pathlib import Path

score_file = Path(os.environ["SCORE_DIR"]) / "puzzle_map_calibration.txt"
if score_file.exists():
    try:
        score = float(score_file.read_text().strip())
    except ValueError:
        score = 0.0
else:
    score = 0.0

print(f"Final score: {score:.3f}")
reward_path = Path("/logs/verifier/reward.txt")
try:
    reward_path.parent.mkdir(parents=True, exist_ok=True)
    reward_path.write_text(f"{score:.3f}")
except PermissionError:
    fallback = Path(".logs/verifier/reward.txt")
    fallback.parent.mkdir(parents=True, exist_ok=True)
    fallback.write_text(f"{score:.3f}")
PY
