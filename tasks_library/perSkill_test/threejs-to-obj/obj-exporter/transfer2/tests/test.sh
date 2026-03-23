#!/bin/bash
set -uo pipefail

mkdir -p /logs/verifier /logs/verifier/outputs /logs/verifier/expected

cp /tests/gen_ground_truth.mjs /root/gen_ground_truth.mjs
node /root/gen_ground_truth.mjs
rm -f /root/gen_ground_truth.mjs

if pytest /tests/test_outputs.py -rA; then
  status=0
else
  status=$?
fi

if [ -f /root/output/safety_barrier.obj ]; then
  cp -f /root/output/safety_barrier.obj /logs/verifier/outputs/safety_barrier.obj
fi

if [ -f /root/ground_truth/safety_barrier.obj ]; then
  cp -f /root/ground_truth/safety_barrier.obj /logs/verifier/expected/safety_barrier.obj
fi

if [ "$status" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

exit "$status"
