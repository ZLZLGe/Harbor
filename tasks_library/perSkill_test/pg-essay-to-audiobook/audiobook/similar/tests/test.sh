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

cp /root/similar_manifest.json /logs/verifier/similar_manifest.json 2>/dev/null || true
cp /root/similar_audiobook.wav /logs/verifier/similar_audiobook.wav 2>/dev/null || true

exit 0
