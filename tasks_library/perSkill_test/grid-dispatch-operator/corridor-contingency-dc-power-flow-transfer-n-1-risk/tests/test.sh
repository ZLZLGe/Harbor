#!/bin/bash
set -u

mkdir -p /logs/verifier

cd /tests
set +e
pytest -q test_outputs.py
status=$?
set -e

if [ "$status" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

exit 0
