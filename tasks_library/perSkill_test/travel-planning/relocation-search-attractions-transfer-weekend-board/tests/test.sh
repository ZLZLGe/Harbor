#!/bin/bash

set -u

mkdir -p /logs/verifier

pytest /tests/test_outputs.py -q
status=$?

if [ "$status" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

if [ -f /app/output/relocation_weekend_board.html ]; then
  cp /app/output/relocation_weekend_board.html /logs/verifier/relocation_weekend_board.html
fi

exit "$status"
