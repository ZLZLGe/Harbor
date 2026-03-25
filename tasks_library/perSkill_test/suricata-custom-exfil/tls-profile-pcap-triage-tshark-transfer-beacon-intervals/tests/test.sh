#!/bin/bash
set -u

mkdir -p /logs/verifier

cd /workspace
python3 -m pytest /tests/test_outputs.py -rA
TEST_EXIT_CODE=$?

if [ "$TEST_EXIT_CODE" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

cp /workspace/outputs/tls_beacon_profile.json /logs/verifier/tls_beacon_profile.json 2>/dev/null || true

exit 0
