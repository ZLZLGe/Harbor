#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier

if python3 /tests/test_outputs.py; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

cp -f /root/transfer1_clean_cut.mp4 /logs/verifier/transfer1_clean_cut.mp4 2>/dev/null || true
cp -f /root/transfer1_redaction_report.json /logs/verifier/transfer1_redaction_report.json 2>/dev/null || true

exit 0
