#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TEST_FILE="${SCRIPT_DIR}/test_outputs.py"

if [ ! -f "$TEST_FILE" ]; then
    echo "ERROR: Could not find test_outputs.py"
    echo "0" > /logs/verifier/reward.txt
    exit 1
fi

set +e
python3 -m pytest "$TEST_FILE" -v
status=$?
set -e

if [ "$status" -eq 0 ]; then
    echo "1" > /logs/verifier/reward.txt
else
    echo "0" > /logs/verifier/reward.txt
fi

exit "$status"
