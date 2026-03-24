#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier

set +e
python3 /tests/test_outputs.py > /logs/verifier/test.log 2>&1
test_status=$?
set -e

if [ "$test_status" -eq 0 ]; then
  printf '1\n' > /logs/verifier/reward.txt
else
  printf '0\n' > /logs/verifier/reward.txt
fi

exit "$test_status"
