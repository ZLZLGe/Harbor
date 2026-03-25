#!/bin/bash

set -u -o pipefail

mkdir -p /logs/verifier

test_exit_code=0
python3 -m pytest /tests/test_outputs.py -rA
test_exit_code=$?

if [ "$test_exit_code" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

exit "$test_exit_code"
