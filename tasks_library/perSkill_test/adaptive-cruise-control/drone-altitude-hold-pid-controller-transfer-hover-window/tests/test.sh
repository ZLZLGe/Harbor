#!/bin/bash
set -euo pipefail

ROOT_DIR="${TASK_ROOT:-/root}"
TEST_FILE="$(cd "$(dirname "$0")" && pwd)/test_outputs.py"
LOG_DIR="/logs/verifier"
TEST_LOG="$LOG_DIR/test.log"
REWARD_FILE="$LOG_DIR/reward.txt"

mkdir -p "$LOG_DIR"

run_status=0

set +e
if [ -f "$ROOT_DIR/simulate_altitude.py" ] && [ -f "$ROOT_DIR/altitude_tuning.yaml" ]; then
    (
        cd "$ROOT_DIR"
        python3 "$ROOT_DIR/simulate_altitude.py"
    ) >>"$TEST_LOG" 2>&1
    run_status=$?
fi

if python3 -m pytest --version >/dev/null 2>&1; then
    TASK_ROOT="$ROOT_DIR" python3 -m pytest "$TEST_FILE" -v >>"$TEST_LOG" 2>&1
    test_status=$?
else
    TASK_ROOT="$ROOT_DIR" TEST_FILE="$TEST_FILE" python3 <<'PY'
import importlib.util
import inspect
import os
import traceback

test_file = os.environ["TEST_FILE"]
spec = importlib.util.spec_from_file_location("task_tests", test_file)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

failures = []
for _, cls in inspect.getmembers(module, inspect.isclass):
    if not cls.__name__.startswith("Test"):
        continue
    instance = cls()
    for name, method in inspect.getmembers(instance, inspect.ismethod):
        if not name.startswith("test_"):
            continue
        try:
            method()
            print(f"PASS {cls.__name__}.{name}")
        except Exception:
            failures.append(f"{cls.__name__}.{name}")
            traceback.print_exc()

if failures:
    raise SystemExit(1)
PY
    test_status=$?
fi
set -e

if [ "$run_status" -eq 0 ] && [ "$test_status" -ne 0 ]; then
    run_status=$test_status
fi

if [ "$run_status" -eq 0 ]; then
    printf '1.0\n' >"$REWARD_FILE"
else
    printf '0.0\n' >"$REWARD_FILE"
fi

exit "$run_status"
