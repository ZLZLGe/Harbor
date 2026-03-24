#!/bin/bash

LOG_ROOT="/logs/verifier"
if ! mkdir -p "$LOG_ROOT/scores" "$LOG_ROOT/solutions" 2>/dev/null; then
  LOG_ROOT=".tmp_logs/verifier"
  mkdir -p "$LOG_ROOT/scores" "$LOG_ROOT/solutions"
fi

cp /output/festival_site_plan.json "$LOG_ROOT/solutions/" 2>/dev/null || true

TEST_SCRIPT="/tests/test_outputs.py"
if [ ! -f "$TEST_SCRIPT" ]; then
  TEST_SCRIPT="tests/test_outputs.py"
fi

python3 "$TEST_SCRIPT" > "$LOG_ROOT/test_output.log" 2>&1
TEST_EXIT_CODE=$?

cat "$LOG_ROOT/test_output.log"

python3 <<'PY'
from pathlib import Path

score_file = Path("/logs/verifier/scores/festival_site_plan.txt")
if not score_file.exists():
    score_file = Path(".tmp_logs/verifier/scores/festival_site_plan.txt")

score = 0.0
if score_file.exists():
    try:
        score = float(score_file.read_text().strip())
    except ValueError:
        score = 0.0

print(f"festival_site_plan: {score:.3f}")

reward_path = Path("/logs/verifier/reward.txt")
if not reward_path.parent.exists():
    reward_path = Path(".tmp_logs/verifier/reward.txt")
reward_path.write_text(f"{score:.3f}")
PY

exit "$TEST_EXIT_CODE"
