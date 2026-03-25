#!/bin/bash
set -u

mkdir -p /logs/verifier

status=0
pytest /tests/test_outputs.py -rA
status=$?

mkdir -p /logs/verifier/outputs
if [ -f /root/output/floor_manifest.json ]; then
  cp /root/output/floor_manifest.json /logs/verifier/outputs/
fi
if [ -d /root/output/floors ]; then
  cp -r /root/output/floors /logs/verifier/outputs/
fi

if [ "$status" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

exit "$status"
