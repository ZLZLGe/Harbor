#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier

if python3 /tests/test_outputs.py > /logs/verifier/test-stdout.txt 2>&1; then
  TEST_EXIT_CODE=0
else
  TEST_EXIT_CODE=$?
fi

cp /logs/verifier/test-stdout.txt /logs/verifier/test_output.txt 2>/dev/null || true
cp /outputs/transfer1_vertical.mp4 /logs/verifier/transfer1_vertical.mp4 2>/dev/null || true

if [ "$TEST_EXIT_CODE" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

exit 0
