#!/bin/bash
set -uo pipefail

mkdir -p /logs/verifier

set +e
pytest /tests/test_outputs.py -q > /logs/verifier/test_output.log 2>&1
test_exit_code=$?
set -e

cat /logs/verifier/test_output.log

if [ "$test_exit_code" -eq 0 ]; then
  echo "1" > /logs/verifier/reward.txt
else
  echo "0" > /logs/verifier/reward.txt
fi

exit "$test_exit_code"
