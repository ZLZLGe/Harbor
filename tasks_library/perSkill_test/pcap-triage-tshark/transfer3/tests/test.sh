#!/bin/bash

mkdir -p /logs/verifier

python3 /tests/test_outputs.py > /logs/verifier/test-stdout.txt 2>&1
PYTEST_EXIT_CODE=$?

if [ $PYTEST_EXIT_CODE -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

cp /root/transfer3_digest_fingerprints.tsv /logs/verifier/transfer3_digest_fingerprints.tsv 2>/dev/null || true
exit 0
