#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier
if python3 /tests/test_outputs.py > /logs/verifier/test-stdout.txt 2>&1; then
  TEST_EXIT_CODE=0
else
  TEST_EXIT_CODE=$?
fi

if [ -d /root ]; then
  find /root -maxdepth 1 -type f \( -name '*.json' -o -name '*.wav' -o -name '*.mp4' -o -name '*.csv' \) -exec cp {} /logs/verifier/ \; || true
fi

if [ "$TEST_EXIT_CODE" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

exit 0
