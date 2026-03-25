#!/bin/bash

mkdir -p /logs/verifier

set +e
python3 -m pytest /tests/test_outputs.py -rA -v
TEST_EXIT_CODE=$?
set -e

cp /root/speech_activity_mask.csv /logs/verifier/speech_activity_mask.csv 2>/dev/null || true
cp /root/activity_summary.json /logs/verifier/activity_summary.json 2>/dev/null || true

if [ "$TEST_EXIT_CODE" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

exit "$TEST_EXIT_CODE"
