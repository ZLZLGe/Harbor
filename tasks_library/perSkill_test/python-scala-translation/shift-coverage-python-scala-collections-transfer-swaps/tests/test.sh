#!/bin/bash

set -u

mkdir -p /logs/verifier

set +e
pytest -q /tests/test_outputs.py > /logs/verifier/output.log 2>&1
test_exit=$?
set -e

if [ "$test_exit" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

exit 0
