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

if [ -f /app/output/landmark_cards.csv ]; then
  cp /app/output/landmark_cards.csv /logs/verifier/landmark_cards.csv
fi

exit "$status"
