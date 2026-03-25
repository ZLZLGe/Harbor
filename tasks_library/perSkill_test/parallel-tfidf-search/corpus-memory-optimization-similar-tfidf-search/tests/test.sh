#!/bin/bash
set -u

mkdir -p /logs/verifier

python -m pytest /tests/test_outputs.py -q
EXIT_CODE=$?

if [ "$EXIT_CODE" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

exit 0
