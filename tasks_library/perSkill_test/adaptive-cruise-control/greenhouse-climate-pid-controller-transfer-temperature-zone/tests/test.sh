#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier

ROOT_DIR="${TASK_ROOT:-/root}"
TEST_FILE="$(cd "$(dirname "$0")" && pwd)/test_outputs.py"
LOG_FILE="/logs/verifier/pytest.log"
REWARD_FILE="/logs/verifier/reward.txt"

simulation_status=0

if [ -f "$ROOT_DIR/simulate_greenhouse.py" ] && [ -f "$ROOT_DIR/greenhouse_tuning.yaml" ]; then
    set +e
    (
        cd "$ROOT_DIR"
        python3 "$ROOT_DIR/simulate_greenhouse.py"
    ) >>"$LOG_FILE" 2>&1
    simulation_status=$?
    set -e
fi

test_status=0
set +e
TASK_ROOT="$ROOT_DIR" python3 -m pytest "$TEST_FILE" -v 2>&1 | tee -a "$LOG_FILE"
test_status=${PIPESTATUS[0]}
set -e

if [ "$simulation_status" -ne 0 ] || [ "$test_status" -ne 0 ]; then
    echo "0.0" > "$REWARD_FILE"
    exit 1
fi

echo "1.0" > "$REWARD_FILE"
