#!/bin/bash

mkdir -p /logs/verifier

set +e
python3 -m pytest /tests/test_outputs.py -rA -v
TEST_EXIT_CODE=$?
set -e

if [ "$TEST_EXIT_CODE" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

cp /root/rooftop_activity_heatmap.npy /logs/verifier/rooftop_activity_heatmap.npy 2>/dev/null || true

exit "$TEST_EXIT_CODE"
