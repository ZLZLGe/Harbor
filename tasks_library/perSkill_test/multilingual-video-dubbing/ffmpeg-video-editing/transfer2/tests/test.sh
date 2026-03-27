#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier

if python3 -m pytest /tests/test_outputs.py -q; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

cp -f /root/transfer2_split_map.json /logs/verifier/ 2>/dev/null || true
cp -f /root/transfer2_part_1.mp4 /logs/verifier/ 2>/dev/null || true
cp -f /root/transfer2_part_2.mp4 /logs/verifier/ 2>/dev/null || true
cp -f /root/transfer2_part_3.mp4 /logs/verifier/ 2>/dev/null || true

exit 0
