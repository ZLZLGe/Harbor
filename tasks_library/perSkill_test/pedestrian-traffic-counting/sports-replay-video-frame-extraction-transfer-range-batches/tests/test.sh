#!/bin/bash
set -u

mkdir -p /logs/verifier

pytest /tests/test_outputs.py
status=$?

if [ "$status" -eq 0 ]; then
  printf '1\n' > /logs/verifier/reward.txt
else
  printf '0\n' > /logs/verifier/reward.txt
fi

exit "$status"
