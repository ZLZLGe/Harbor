#!/bin/bash

set -euo pipefail

mkdir -p /logs/verifier

cd /tests

test_status=0
set +e
python3 -m pytest /tests/test_outputs.py -q 2>&1 | tee /logs/verifier/test.log
test_status=${PIPESTATUS[0]}
set -e

if [ "$test_status" -eq 0 ]; then
  printf '1.0\n' > /logs/verifier/reward.txt
else
  printf '0.0\n' > /logs/verifier/reward.txt
fi

exit "$test_status"
