#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier

if python3 /tests/test_outputs.py; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

cp -f /root/transfer1_review_manifest.json /logs/verifier/transfer1_review_manifest.json 2>/dev/null || true
cp -f /root/transfer1_all_segments.json /logs/verifier/transfer1_all_segments.json 2>/dev/null || true

exit 0
