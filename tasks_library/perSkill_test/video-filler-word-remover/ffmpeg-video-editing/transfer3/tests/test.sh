#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier

if python3 /tests/test_outputs.py; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

cp -f /root/transfer3_window_index.json /logs/verifier/transfer3_window_index.json 2>/dev/null || true
cp -rf /root/transfer3_window_pack /logs/verifier/transfer3_window_pack 2>/dev/null || true

exit 0
