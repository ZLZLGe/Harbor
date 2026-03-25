#!/bin/bash
set -u

mkdir -p /logs/verifier

pytest -q /tests/test_outputs.py
TEST_EXIT=$?

if [ $TEST_EXIT -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

exit $TEST_EXIT
