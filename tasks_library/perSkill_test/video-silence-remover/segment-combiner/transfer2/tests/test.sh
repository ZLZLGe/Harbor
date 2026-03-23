#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier

if python3 /tests/test_outputs.py; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

cp -f /root/transfer2_overlap_alerts.json /logs/verifier/transfer2_overlap_alerts.json 2>/dev/null || true

exit 0
