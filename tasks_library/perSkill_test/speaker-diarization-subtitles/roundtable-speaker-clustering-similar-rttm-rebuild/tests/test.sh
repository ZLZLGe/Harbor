#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier /logs/agent

set +e
python3 -m pytest /tests/test_outputs.py -rA -v
TEST_EXIT_CODE=$?
set -e

cp /root/panel_diarization.rttm /logs/verifier/panel_diarization.rttm 2>/dev/null || true
python3 /tests/test_outputs.py --score /logs/verifier/score.json || true

if [ $TEST_EXIT_CODE -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

exit $TEST_EXIT_CODE
