#!/bin/bash
set -u

python3 /tests/test_outputs.py
RESULT=$?

if [ "$RESULT" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

exit "$RESULT"
