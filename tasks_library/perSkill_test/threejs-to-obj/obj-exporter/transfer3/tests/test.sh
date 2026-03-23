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

if [ -f /root/output/light_canopy.obj ]; then
  cp -f /root/output/light_canopy.obj /logs/verifier/outputs/light_canopy.obj
fi

if [ -f /root/ground_truth/light_canopy.obj ]; then
  cp -f /root/ground_truth/light_canopy.obj /logs/verifier/expected/light_canopy.obj
fi

if [ "$status" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

exit "$status"
