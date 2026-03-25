#!/bin/bash
set -u

mkdir -p /logs/verifier

cd /root
pytest /tests/test_outputs.py -q > /logs/verifier/pytest.log 2>&1
status=$?

if [ "$status" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

cat /logs/verifier/pytest.log
exit 0
