#!/bin/bash

set -euo pipefail

TASK_ROOT="${TASK_ROOT:-/root}"
TEST_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="/logs/verifier"

mkdir -p "$LOG_DIR"
cd "$TASK_ROOT"

status=0

set +e
if [ -f "$TASK_ROOT/autoscaling_replay.py" ]; then
    python3 "$TASK_ROOT/autoscaling_replay.py" >"$LOG_DIR/replay.log" 2>&1
    status=$?
fi

if [ "$status" -eq 0 ]; then
    python3 -m pytest "$TEST_DIR/test_outputs.py" -v >"$LOG_DIR/pytest.log" 2>&1
    status=$?
fi
set -e

if [ "$status" -eq 0 ]; then
    echo "1.0" >"$LOG_DIR/reward.txt"
else
    echo "0.0" >"$LOG_DIR/reward.txt"
fi

if [ -f "$LOG_DIR/replay.log" ]; then
    cat "$LOG_DIR/replay.log"
fi

if [ -f "$LOG_DIR/pytest.log" ]; then
    cat "$LOG_DIR/pytest.log"
fi

exit "$status"
