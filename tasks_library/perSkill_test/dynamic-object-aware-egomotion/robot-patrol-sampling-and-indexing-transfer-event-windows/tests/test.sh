#!/bin/bash
set -u

mkdir -p /logs/verifier

pytest -q /tests/test_outputs.py
TEST_EXIT_CODE=$?

if [ "$TEST_EXIT_CODE" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

cp /root/event_windows.json /logs/verifier/event_windows.json 2>/dev/null || true

exit "$TEST_EXIT_CODE"
