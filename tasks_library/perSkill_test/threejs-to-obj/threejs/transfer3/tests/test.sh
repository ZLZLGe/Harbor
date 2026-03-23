#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier /root/ground_truth
chmod 777 /logs/verifier

cp /tests/gen_ground_truth.mjs /root/gen_ground_truth.mjs
node /root/gen_ground_truth.mjs
rm -f /root/gen_ground_truth.mjs

python3 -m pytest /tests/test_outputs.py -rA

status=$?

mkdir -p /logs/verifier/outputs /logs/verifier/expected
if [ -f /root/output/leaf_parts_index.json ]; then
  cp -f /root/output/leaf_parts_index.json /logs/verifier/outputs/
fi
if [ -f /root/ground_truth/leaf_parts_index.json ]; then
  cp -f /root/ground_truth/leaf_parts_index.json /logs/verifier/expected/
fi

if [ "$status" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

exit "$status"
