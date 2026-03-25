#!/bin/bash

mkdir -p /logs/verifier

set +e
python3 -m pytest /tests/test_outputs.py -rA -v | tee /logs/verifier/test_output.log
EXIT_CODE=${PIPESTATUS[0]}
set -e

if [ "$EXIT_CODE" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

exit 0
