#!/bin/bash

set -euo pipefail

set +e
python3 /tests/test_outputs.py
status=$?
set -e

if [ $status -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

if [ -f "/root/data/bodyweight_clamp_audit.json" ]; then
  cp /root/data/bodyweight_clamp_audit.json /logs/verifier/bodyweight_clamp_audit.json
fi

exit $status
