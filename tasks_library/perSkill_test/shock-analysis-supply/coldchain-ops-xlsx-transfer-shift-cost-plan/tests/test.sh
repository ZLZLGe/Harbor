#!/bin/bash

mkdir -p /logs/verifier

if [ -f /root/coldchain-ops-plan.xlsx ]; then
  python3 /root/.codex/skills/xlsx/recalc.py /root/coldchain-ops-plan.xlsx 90 >/tmp/coldchain-ops-test-recalc.json 2>/tmp/coldchain-ops-test-recalc.err || true
fi

set +e
cd /root
pytest /tests/test_outputs.py -q
TEST_EXIT_CODE=$?
set -e

if [ $TEST_EXIT_CODE -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

if [ -f /root/coldchain-ops-plan.xlsx ]; then
  cp /root/coldchain-ops-plan.xlsx /logs/verifier/coldchain-ops-plan.xlsx
fi

exit 0
