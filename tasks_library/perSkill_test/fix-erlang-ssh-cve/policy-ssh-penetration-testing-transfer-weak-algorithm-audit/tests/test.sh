#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier

test_log=/logs/verifier/test.log
reward_file=/logs/verifier/reward.txt

set +e
python3 -m pytest -q /tests/test_outputs.py >"$test_log" 2>&1
test_status=$?
set -e

if [ "$test_status" -eq 0 ]; then
    printf '1.0\n' >"$reward_file"
else
    printf '0.0\n' >"$reward_file"
fi

cat "$test_log"
exit "$test_status"
