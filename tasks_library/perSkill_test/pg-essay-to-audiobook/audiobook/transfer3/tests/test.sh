#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier

python3 /tests/test_outputs.py > /logs/verifier/test-stdout.txt 2>&1
TEST_EXIT=$?

if [ "$TEST_EXIT" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

cp /root/transfer3_cues.txt /logs/verifier/transfer3_cues.txt 2>/dev/null || true
cp /root/transfer3_casefile_audio.wav /logs/verifier/transfer3_casefile_audio.wav 2>/dev/null || true

exit 0
