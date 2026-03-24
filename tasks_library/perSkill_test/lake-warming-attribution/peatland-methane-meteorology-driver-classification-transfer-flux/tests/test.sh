#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier

set +e
python3 -m pytest -q /tests/test_outputs.py
test_status=$?
set -e

if [ "$test_status" -eq 0 ]; then
    printf '1.0\n' > /logs/verifier/reward.txt
else
    printf '0.0\n' > /logs/verifier/reward.txt
fi

exit "$test_status"
