#!/bin/bash
set +e

mkdir -p /logs/verifier

python3 /tests/test_outputs.py > /logs/verifier/test-stdout.txt 2>&1
TEST_EXIT_CODE=$?

if [ $TEST_EXIT_CODE -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

cp /root/transfer3_metadata_mapping_report.md /logs/verifier/transfer3_metadata_mapping_report.md 2>/dev/null || true
exit 0
