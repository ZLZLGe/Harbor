#!/bin/bash

set -uo pipefail

mkdir -p /logs/verifier

python -m pytest -rA -v /tests/test_outputs.py | tee /logs/verifier/test_output.log
TEST_EXIT=${PIPESTATUS[0]}

if [ "${TEST_EXIT}" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

exit 0
