#!/bin/bash
set -euo pipefail

VERIFY_LOG_DIR="${VERIFY_LOG_DIR:-/logs/verifier}"
CTRF_PATH="${CTRF_PATH:-$VERIFY_LOG_DIR/ctrf.json}"
TEST_FILE="${TEST_FILE:-/tests/test_outputs.py}"
export VERIFY_LOG_DIR CTRF_PATH TEST_FILE

if command -v pip3 >/dev/null 2>&1; then
  pip3 install --break-system-packages pytest==8.3.4 pytest-json-ctrf==0.3.5 2>/dev/null || \
  pip3 install pytest==8.3.4 pytest-json-ctrf==0.3.5 2>/dev/null || true
fi

mkdir -p "$VERIFY_LOG_DIR/scores"
mkdir -p "$VERIFY_LOG_DIR/solutions"

cp "${OUTPUT_PATH:-/output/mars_colony_plan.json}" "$VERIFY_LOG_DIR/solutions/" 2>/dev/null || true

if command -v pytest >/dev/null 2>&1; then
  pytest "$TEST_FILE" -v --tb=short --ctrf "$CTRF_PATH" > "$VERIFY_LOG_DIR/test_output.log" 2>&1
elif python3 -m pytest --version >/dev/null 2>&1; then
  python3 -m pytest "$TEST_FILE" -v --tb=short > "$VERIFY_LOG_DIR/test_output.log" 2>&1
else
  python3 "$TEST_FILE" > "$VERIFY_LOG_DIR/test_output.log" 2>&1
fi

cat "$VERIFY_LOG_DIR/test_output.log"

python3 - <<'PY'
import os
from pathlib import Path

verify_log_dir = Path(os.environ.get("VERIFY_LOG_DIR", "/logs/verifier"))
score_file = verify_log_dir / "scores" / "mars_colony_plan.txt"

if score_file.exists():
    try:
        score = float(score_file.read_text().strip())
    except ValueError:
        score = 0.0
else:
    score = 0.0

print(f"mars_colony_plan: {score:.3f}")
print(f"Final score: {score:.3f}")

(verify_log_dir / "reward.txt").write_text(f"{score:.3f}")
PY
