#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier
chmod 777 /logs/verifier

cp /tests/gen_ground_truth.mjs /root/gen_ground_truth.mjs
node /root/gen_ground_truth.mjs
rm -f /root/gen_ground_truth.mjs

set +e
python3 /tests/test_outputs.py
status=$?
set -e

mkdir -p /logs/verifier/outputs /logs/verifier/expected
if [ -d /root/output ]; then
  cp -r /root/output /logs/verifier/outputs/
fi
if [ -d /root/ground_truth ]; then
  cp -r /root/ground_truth /logs/verifier/expected/
fi

if [ $status -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

exit $status
