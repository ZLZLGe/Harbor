#!/bin/bash
set -e

cp /tests/expected_state_spans.json /root/expected_state_spans.json

mkdir -p /logs/verifier

python3 -m pytest /tests/test_outputs.py -rA -v
TEST_EXIT=$?

cp /root/pred_line_state_spans.json /logs/verifier/pred_line_state_spans.json 2>/dev/null || true

if [ "$TEST_EXIT" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

exit "$TEST_EXIT"
