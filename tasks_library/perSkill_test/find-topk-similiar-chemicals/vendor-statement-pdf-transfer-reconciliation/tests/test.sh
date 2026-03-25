#!/bin/bash

set -u

mkdir -p /logs/verifier

set +e
pytest -q /tests/test_outputs.py
TEST_EXIT_CODE=$?
set -e

if [ "$TEST_EXIT_CODE" -eq 0 ]; then
    echo "1" > /logs/verifier/reward.txt
else
    echo "0" > /logs/verifier/reward.txt
fi

exit 0
