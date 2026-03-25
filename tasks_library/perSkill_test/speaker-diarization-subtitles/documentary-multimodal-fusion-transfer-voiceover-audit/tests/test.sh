#!/bin/bash
set -u

mkdir -p /logs/verifier

python3 -m pytest /tests/test_outputs.py -rA -v
TEST_EXIT_CODE=$?

cp /root/narration_audit.json /logs/verifier/narration_audit.json 2>/dev/null || true

if [ "$TEST_EXIT_CODE" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

exit "$TEST_EXIT_CODE"
