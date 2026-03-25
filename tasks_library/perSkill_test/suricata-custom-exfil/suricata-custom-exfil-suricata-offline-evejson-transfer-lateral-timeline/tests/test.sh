#!/bin/bash

mkdir -p /logs/verifier

cd /root

set +e
python3 -m pytest /tests/test_outputs.py -rA -v
test_exit_code=$?
set -e

if [ "$test_exit_code" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

cp /root/answer/lateral-timeline.csv /logs/verifier/lateral-timeline.csv 2>/dev/null || true

exit 0
