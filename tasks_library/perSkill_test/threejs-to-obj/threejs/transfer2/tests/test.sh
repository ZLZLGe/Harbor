#!/bin/bash
set -uo pipefail

mkdir -p /logs/verifier
chmod 777 /logs/verifier

if python3 -m pytest /tests/test_outputs.py -rA; then
  status=0
else
  status=$?
fi

if [ $status -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

exit $status
