#!/bin/bash
set -u

mkdir -p /logs/verifier /logs/agent

set +e
python3 -m pytest /tests/test_outputs.py -rA > /logs/verifier/pytest.log 2>&1
status=$?
set -e

if [ "$status" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

if [ -f /root/Webinar-Rehearsal-notes-ready.pptx ]; then
  cp /root/Webinar-Rehearsal-notes-ready.pptx /logs/agent/
fi

cat /logs/verifier/pytest.log
exit "$status"
