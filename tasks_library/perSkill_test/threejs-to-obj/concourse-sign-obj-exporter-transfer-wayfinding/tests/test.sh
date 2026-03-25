#!/bin/bash
set -u

mkdir -p /logs/verifier

status=0
python3 -m pytest /tests/test_outputs.py -rA
status=$?

mkdir -p /logs/verifier/outputs
if [ -f /root/output/wayfinding_sign.obj ]; then
  cp /root/output/wayfinding_sign.obj /logs/verifier/outputs/wayfinding_sign.obj
fi

if [ "$status" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

exit "$status"
