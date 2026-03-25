#!/bin/bash
set -uo pipefail

mkdir -p /logs/verifier
mkdir -p /logs/agent

status=0
pytest /tests/test_outputs.py -rA || status=$?

if [ "$status" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

if [ -f /root/GreenGrid-Proposal-tailored.pptx ]; then
  cp /root/GreenGrid-Proposal-tailored.pptx /logs/agent/GreenGrid-Proposal-tailored.pptx
fi

exit "$status"
