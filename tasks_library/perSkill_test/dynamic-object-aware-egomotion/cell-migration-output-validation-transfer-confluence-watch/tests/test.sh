#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier

if python3 -m pytest /tests/test_outputs.py -rA -v; then
  TEST_EXIT_CODE=0
else
  TEST_EXIT_CODE=$?
fi

cp /root/pred_cell_activity.json /logs/verifier/pred_cell_activity.json 2>/dev/null || true
cp /root/pred_cell_activity_masks.npz /logs/verifier/pred_cell_activity_masks.npz 2>/dev/null || true

if [ "$TEST_EXIT_CODE" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

exit "$TEST_EXIT_CODE"
