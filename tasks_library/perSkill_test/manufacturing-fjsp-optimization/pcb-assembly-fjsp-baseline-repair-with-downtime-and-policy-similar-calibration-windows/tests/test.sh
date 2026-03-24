#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier

TEST_LOG=/logs/verifier/pytest.log
REWARD_FILE=/logs/verifier/reward.txt

set +e
pytest /tests/test_outputs.py -rA >"$TEST_LOG" 2>&1
test_status=$?
set -e

if [ "$test_status" -eq 0 ]; then
  printf '1.0\n' >"$REWARD_FILE"
else
  printf '0.0\n' >"$REWARD_FILE"
fi

cat "$TEST_LOG"
exit "$test_status"
