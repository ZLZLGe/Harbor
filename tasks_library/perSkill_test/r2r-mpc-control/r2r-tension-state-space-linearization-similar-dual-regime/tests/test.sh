#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TASK_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

LOG_DIR="/logs/verifier"
if ! mkdir -p "$LOG_DIR" 2>/dev/null; then
  LOG_DIR="$TASK_DIR/.logs/verifier"
  mkdir -p "$LOG_DIR"
fi

if [ -f /root/dual_regime_config.json ]; then
  TEST_FILE="/tests/test_outputs.py"
else
  TEST_FILE="$TASK_DIR/tests/test_outputs.py"
fi

set +e
python3 "$TEST_FILE"
TEST_EXIT_CODE=$?
set -e

if [ $TEST_EXIT_CODE -eq 0 ]; then
  echo "1" > "$LOG_DIR/reward.txt"
else
  echo "0" > "$LOG_DIR/reward.txt"
fi

if [ -f /root/artifacts/r2r_dual_regime_linearization.json ]; then
  cp /root/artifacts/r2r_dual_regime_linearization.json "$LOG_DIR/" 2>/dev/null || true
elif [ -f "$TASK_DIR/artifacts/r2r_dual_regime_linearization.json" ]; then
  cp "$TASK_DIR/artifacts/r2r_dual_regime_linearization.json" "$LOG_DIR/" 2>/dev/null || true
fi

exit 0
