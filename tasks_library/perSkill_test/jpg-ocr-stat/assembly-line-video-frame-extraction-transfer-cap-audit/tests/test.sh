#!/bin/bash

set -euo pipefail

mkdir -p /logs/verifier

cd /app/workspace

test_status=0
set +e
python3 /tests/test_outputs.py >/logs/verifier/test_output.txt 2>&1
test_status=$?
set -e

if [ "$test_status" -eq 0 ]; then
    printf '1.0\n' >/logs/verifier/reward.txt
else
    printf '0.0\n' >/logs/verifier/reward.txt
fi

exit "$test_status"
