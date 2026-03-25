#!/bin/bash
set -u -o pipefail

mkdir -p /logs/verifier

pytest /tests/test_outputs.py -q
TEST_EXIT_CODE=$?

cp /root/goalmouth_occupancy.csv /logs/verifier/goalmouth_occupancy.csv 2>/dev/null || true

if [ "$TEST_EXIT_CODE" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

exit "$TEST_EXIT_CODE"
