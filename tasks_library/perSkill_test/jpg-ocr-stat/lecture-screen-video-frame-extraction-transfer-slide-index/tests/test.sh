#!/bin/bash

set -euo pipefail

mkdir -p /logs/verifier

cd /app/workspace

test_status=0
set +e
python3 /tests/test_outputs.py > /logs/verifier/test.log 2>&1
test_status=$?
set -e

if [ "$test_status" -eq 0 ]; then
    echo "1.0" > /logs/verifier/reward.txt
else
    echo "0.0" > /logs/verifier/reward.txt
fi

exit "$test_status"
