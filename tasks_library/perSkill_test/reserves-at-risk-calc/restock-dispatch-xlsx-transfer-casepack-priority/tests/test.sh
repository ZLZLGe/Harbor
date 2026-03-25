#!/bin/bash
set -u -o pipefail

mkdir -p /logs/verifier

if [ -f /root/output/restock_dispatch_board.xlsx ]; then
  python3 /root/.codex/skills/xlsx/recalc.py /root/output/restock_dispatch_board.xlsx 60 > /logs/verifier/recalc.json 2>&1 || true
fi

set +e
cd /root
python3 -m pytest /tests/test_outputs.py -rA
TEST_EXIT_CODE=$?
set -e

if [ $TEST_EXIT_CODE -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

if [ -f /root/output/restock_dispatch_board.xlsx ]; then
  cp /root/output/restock_dispatch_board.xlsx /logs/verifier/restock_dispatch_board.xlsx
fi

exit 0
