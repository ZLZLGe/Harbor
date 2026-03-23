#!/bin/bash
set -uo pipefail

mkdir -p /logs/verifier /logs/verifier/outputs /logs/verifier/expected

cp /tests/gen_ground_truth.mjs /root/gen_ground_truth.mjs
node /root/gen_ground_truth.mjs
rm -f /root/gen_ground_truth.mjs

if python3 -m pytest /tests/test_outputs.py -rA; then
  status=0
else
  status=$?
fi

if [ -f /root/output/studio_display.obj ]; then
  cp -f /root/output/studio_display.obj /logs/verifier/outputs/studio_display.obj
fi
if [ -f /root/ground_truth/studio_display.obj ]; then
  cp -f /root/ground_truth/studio_display.obj /logs/verifier/expected/studio_display.obj
fi

if [ "$status" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

exit "$status"
