#!/bin/bash

set -u

mkdir -p /logs/verifier

python3 -m pytest /tests/test_outputs.py -rA
test_exit_code=$?

if [ "$test_exit_code" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

if [ -f "/root/data/wilks_division_scoreboard.xlsx" ]; then
  cp /root/data/wilks_division_scoreboard.xlsx /logs/verifier/wilks_division_scoreboard.xlsx
fi

exit "$test_exit_code"
