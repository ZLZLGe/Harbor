#!/bin/bash

mkdir -p /logs/verifier

set +e
python3 /tests/test_outputs.py
TEST_EXIT_CODE=$?
set -e

if [ -f /logs/verifier/reward.txt ]; then
    cat /logs/verifier/reward.txt
else
    echo "0.0" > /logs/verifier/reward.txt
    cat /logs/verifier/reward.txt
fi

exit 0
