#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier
cd /root

if python3 /tests/test_outputs.py; then
  echo "1" > /logs/verifier/reward.txt
else
  echo "0" > /logs/verifier/reward.txt
fi

cp /root/*.png /logs/verifier/ 2>/dev/null || true
cp /root/*.gif /logs/verifier/ 2>/dev/null || true
cp /root/*.csv /logs/verifier/ 2>/dev/null || true
exit 0
