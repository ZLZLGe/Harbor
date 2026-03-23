#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier
if python3 /tests/test_outputs.py; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

if [ -f /root/transfer2_quiet_intervals.json ]; then
  cp /root/transfer2_quiet_intervals.json /logs/verifier/
fi

exit 0
