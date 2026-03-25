#!/bin/bash

mkdir -p /logs/verifier

set +e
pytest /tests/test_outputs.py -rA
status=$?
set -e

if [ -d "/root/output/zones" ]; then
  mkdir -p /logs/verifier/outputs
  cp -r /root/output/zones /logs/verifier/outputs/
fi

if [ "$status" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

exit "$status"
