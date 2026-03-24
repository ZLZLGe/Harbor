#!/bin/bash

set -euo pipefail

TASK_ROOT="${TASK_ROOT:-/root}"
TEST_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="/logs/verifier"
LOG_FILE="$LOG_DIR/test.log"
REWARD_FILE="$LOG_DIR/reward.txt"

mkdir -p "$LOG_DIR"
: >"$LOG_FILE"

cd "$TASK_ROOT"

status=0

set +e
if [ -f "$TASK_ROOT/greenhouse_replay.py" ]; then
    python3 "$TASK_ROOT/greenhouse_replay.py" >>"$LOG_FILE" 2>&1
    status=$?
fi

pytest "$TEST_DIR/test_outputs.py" -v >>"$LOG_FILE" 2>&1
test_status=$?
if [ "$status" -eq 0 ] && [ "$test_status" -ne 0 ]; then
    status=$test_status
fi
set -e

if [ "$status" -eq 0 ]; then
    echo "1.0" >"$REWARD_FILE"
else
    echo "0.0" >"$REWARD_FILE"
fi

exit "$status"
