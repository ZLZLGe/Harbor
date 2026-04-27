#!/usr/bin/env bash
set -u

mkdir -p /logs/verifier
if python3 /tests/test_flake_triage.py > /logs/verifier/test.log 2>&1; then
  echo 1 > /logs/verifier/reward.txt
  cat /logs/verifier/test.log
else
  echo 0 > /logs/verifier/reward.txt
  cat /logs/verifier/test.log
fi

exit 0
