#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier
cd /root

if pytest /tests/test_outputs.py --ctrf /logs/verifier/ctrf-report.json -q; then
  echo "1" > /logs/verifier/reward.txt
else
  echo "0" > /logs/verifier/reward.txt
fi

cp /root/*.json /logs/verifier/ 2>/dev/null || true
cp /root/*.jsonl /logs/verifier/ 2>/dev/null || true
exit 0
