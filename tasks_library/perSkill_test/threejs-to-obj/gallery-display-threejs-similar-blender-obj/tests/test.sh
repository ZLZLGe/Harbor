#!/bin/bash
set -u

mkdir -p /logs/verifier
chmod 777 /logs/verifier

status=0

cp /tests/gen_ground_truth.mjs /root/gen_ground_truth.mjs
node /root/gen_ground_truth.mjs
ground_truth_status=$?
rm -f /root/gen_ground_truth.mjs

if [ "$ground_truth_status" -ne 0 ]; then
  status=$ground_truth_status
else
  pytest -q /tests/test_outputs.py
  status=$?
fi

mkdir -p /logs/verifier/outputs /logs/verifier/expected

if [ -f /root/output/display.obj ]; then
  cp /root/output/display.obj /logs/verifier/outputs/display.obj
fi

if [ -f /root/ground_truth/display_points.json ]; then
  cp /root/ground_truth/display_points.json /logs/verifier/expected/display_points.json
fi

if [ "$status" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

exit "$status"
