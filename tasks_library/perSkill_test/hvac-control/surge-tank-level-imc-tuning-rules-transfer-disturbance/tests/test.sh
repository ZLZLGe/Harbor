#!/bin/bash

mkdir -p /logs/verifier

cd /root
python3 -m pytest /tests/test_outputs.py -q
TEST_EXIT_CODE=$?

if [ "$TEST_EXIT_CODE" -eq 0 ]; then
  echo "1" > /logs/verifier/reward.txt
else
  echo "0" > /logs/verifier/reward.txt
fi

cp /root/surge_tank_level_report.json /logs/verifier/ 2>/dev/null || true

exit 0
