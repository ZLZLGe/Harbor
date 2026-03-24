#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier

test_status=0

set +e
python3 /tests/test_outputs.py > /logs/verifier/test_stdout.log 2> /logs/verifier/test_stderr.log
test_status=$?
set -e

if [ "$test_status" -eq 0 ]; then
    printf '1.0\n' > /logs/verifier/reward.txt
else
    printf '0.0\n' > /logs/verifier/reward.txt
fi

exit "$test_status"
