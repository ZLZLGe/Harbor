#!/bin/bash

mkdir -p /logs/verifier

python3 /tests/test_outputs.py > /logs/verifier/test-stdout.txt 2>&1
PYTEST_EXIT_CODE=$?

if [ $PYTEST_EXIT_CODE -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

cp /root/similar_request_audit.csv /logs/verifier/similar_request_audit.csv 2>/dev/null || true
exit 0
