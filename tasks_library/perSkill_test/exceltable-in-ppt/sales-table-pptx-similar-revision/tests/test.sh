#!/bin/bash
set -u

mkdir -p /logs/verifier

pytest -q /tests/test_outputs.py
status=$?

if [ "$status" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

if [ -f /root/results-table-revision.pptx ]; then
  cp /root/results-table-revision.pptx /logs/verifier/results-table-revision.pptx 2>/dev/null || true
fi

exit "$status"
