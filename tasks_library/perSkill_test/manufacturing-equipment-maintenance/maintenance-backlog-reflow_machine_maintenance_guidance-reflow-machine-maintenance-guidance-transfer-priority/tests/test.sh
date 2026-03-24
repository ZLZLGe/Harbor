#!/usr/bin/env bash
set -euo pipefail

mkdir -p /logs/verifier

test_status=0
set +e
pytest -rA /tests/test_outputs.py
test_status=$?
set -e

if [ "$test_status" -eq 0 ]; then
    printf '1.0\n' > /logs/verifier/reward.txt
else
    printf '0.0\n' > /logs/verifier/reward.txt
fi

exit "$test_status"
