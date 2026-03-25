#!/bin/bash
set -u

mkdir -p /logs/verifier

set +e
pytest -q /tests/test_outputs.py
test_exit_code=$?
set -e

if [ "$test_exit_code" -eq 0 ]; then
    echo "1" > /logs/verifier/reward.txt
else
    echo "0" > /logs/verifier/reward.txt
fi

exit 0
