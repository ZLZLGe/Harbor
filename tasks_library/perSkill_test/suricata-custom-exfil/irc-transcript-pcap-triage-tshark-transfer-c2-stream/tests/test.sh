#!/usr/bin/env bash
set -u

mkdir -p /logs/verifier

cd /workspace
python3 -m pytest /tests/test_outputs.py -rA -v
test_exit_code=$?

if [ "$test_exit_code" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

cp /workspace/outputs/irc_c2_transcript.txt /logs/verifier/irc_c2_transcript.txt 2>/dev/null || true

exit 0
