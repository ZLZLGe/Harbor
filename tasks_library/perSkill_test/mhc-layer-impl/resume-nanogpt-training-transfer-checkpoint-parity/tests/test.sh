#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TASK_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REWARD_DIR="/logs/verifier"

mkdir -p "$REWARD_DIR"

TEST_STATUS=0

set +e
if [ -x /solution/solve.sh ]; then
  /solution/solve.sh
else
  bash "$TASK_DIR/solution/solve.sh"
fi
SOLVE_STATUS=$?

if [ "$SOLVE_STATUS" -eq 0 ]; then
  if [ -f /tests/test_outputs.py ]; then
    python3 -m pytest -q /tests/test_outputs.py
  else
    python3 -m pytest -q "$TASK_DIR/tests/test_outputs.py"
  fi
  TEST_STATUS=$?
else
  TEST_STATUS=$SOLVE_STATUS
fi
set -e

if [ "$TEST_STATUS" -eq 0 ]; then
  printf '1.0\n' > "$REWARD_DIR/reward.txt"
else
  printf '0.0\n' > "$REWARD_DIR/reward.txt"
fi

exit "$TEST_STATUS"
