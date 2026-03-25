#!/bin/bash

mkdir -p /logs/verifier

cd /root

set +e
python3 -m pytest /tests/test_outputs.py -rA -v
TEST_EXIT_CODE=$?
set -e

if [ "$TEST_EXIT_CODE" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

if [ -f /root/reservoir-resilience-model.xlsx ]; then
  cp /root/reservoir-resilience-model.xlsx /logs/verifier/reservoir-resilience-model.xlsx
fi

exit 0
