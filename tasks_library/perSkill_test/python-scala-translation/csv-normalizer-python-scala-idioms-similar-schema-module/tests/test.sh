#!/bin/bash
set -u

mkdir -p /logs/verifier
cd /root

set +e
python3 -m pytest -q /tests/test_outputs.py > /logs/verifier/output.log 2>&1
status=$?
set -e

if [ "$status" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

exit 0
