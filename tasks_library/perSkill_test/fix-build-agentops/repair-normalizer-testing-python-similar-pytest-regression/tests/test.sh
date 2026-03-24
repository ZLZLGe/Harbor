#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier

cd /workspace/text-normalizer

set +e
python -m pytest /tests/test_outputs.py -rA -v > /logs/verifier/pytest.log 2>&1
test_status=$?
set -e

cat /logs/verifier/pytest.log

if [ "$test_status" -eq 0 ]; then
  echo "1.0" > /logs/verifier/reward.txt
else
  echo "0.0" > /logs/verifier/reward.txt
fi

exit "$test_status"
