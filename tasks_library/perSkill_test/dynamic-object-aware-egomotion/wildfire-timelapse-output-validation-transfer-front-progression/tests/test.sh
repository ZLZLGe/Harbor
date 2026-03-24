#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier

if python3 -m pytest /tests/test_outputs.py -rA -v; then
  PYTEST_EXIT_CODE=0
else
  PYTEST_EXIT_CODE=$?
fi

cp /root/pred_fire_progression.json /logs/verifier/pred_fire_progression.json 2>/dev/null || true
cp /root/pred_fireline_masks.npz /logs/verifier/pred_fireline_masks.npz 2>/dev/null || true

if [ "$PYTEST_EXIT_CODE" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

exit "$PYTEST_EXIT_CODE"
