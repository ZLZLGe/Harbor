#!/bin/bash
set -u

mkdir -p /logs/verifier

python3 -m pytest /tests/test_outputs.py -rA -v
test_exit_code=$?

cp /root/podium_speaking_times.csv /logs/verifier/podium_speaking_times.csv 2>/dev/null || true

if [ "$test_exit_code" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

exit "$test_exit_code"
