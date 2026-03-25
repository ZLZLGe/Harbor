#!/bin/bash
set -u

mkdir -p /logs/verifier

cd /tests
set +e
python3 -m pytest /tests/test_outputs.py -rA -v > /logs/verifier/test-stdout.txt 2>&1
test_exit=$?
set -e

if [ "$test_exit" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

exit 0
