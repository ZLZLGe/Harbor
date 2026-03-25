#!/bin/bash
set -u

mkdir -p /logs/verifier

python3 -m pytest /tests/test_outputs.py -rA -v
test_exit_code=$?

cp /root/channel_swap_alerts.json /logs/verifier/channel_swap_alerts.json 2>/dev/null || true

if [ "$test_exit_code" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

exit "$test_exit_code"
