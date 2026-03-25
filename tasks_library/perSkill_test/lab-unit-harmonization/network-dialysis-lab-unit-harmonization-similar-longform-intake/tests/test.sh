#!/bin/bash
set -uo pipefail

mkdir -p /logs/verifier

cd /root

set +e
python3 -m pytest /tests/test_outputs.py -q > /logs/verifier/test_output.log 2>&1
status=$?
set -e

if [ "$status" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

cat /logs/verifier/test_output.log
exit "$status"
