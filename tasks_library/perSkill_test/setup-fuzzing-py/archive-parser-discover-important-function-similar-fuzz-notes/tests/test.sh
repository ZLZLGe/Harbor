#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier
set +e
python /tests/test_outputs.py
test_status=$?
set -e

if [ "$test_status" -eq 0 ]; then
  printf '1.0\n' > /logs/verifier/reward.txt
else
  printf '0.0\n' > /logs/verifier/reward.txt
fi

if [ -f /app/archive_fuzz_targets.md ]; then
  cp /app/archive_fuzz_targets.md /logs/verifier/archive_fuzz_targets.md
fi

exit "$test_status"
