#!/bin/bash
set -u

mkdir -p /logs/verifier

python3 -m pytest /tests/test_outputs.py -q
TEST_EXIT_CODE=$?

if [ "$TEST_EXIT_CODE" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

cp /root/room_state_timeline.json /logs/verifier/room_state_timeline.json 2>/dev/null || true
cp /root/seat_usage_csr.npz /logs/verifier/seat_usage_csr.npz 2>/dev/null || true

exit "$TEST_EXIT_CODE"
