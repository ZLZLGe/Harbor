#!/bin/bash
set -u

mkdir -p /logs/verifier

pytest /tests/test_outputs.py -q
test_exit_code=$?

if [ "$test_exit_code" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

cp /root/speaker_timeline.json /logs/verifier/speaker_timeline.json 2>/dev/null || true

exit "$test_exit_code"
