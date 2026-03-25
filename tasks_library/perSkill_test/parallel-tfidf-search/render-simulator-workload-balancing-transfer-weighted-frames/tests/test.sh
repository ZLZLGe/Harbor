#!/bin/bash

set -u -o pipefail

mkdir -p /logs/verifier

python -m pytest /tests/test_outputs.py -rA -v 2>&1 | tee /logs/verifier/test_output.log
EXIT_CODE=${PIPESTATUS[0]}

if [ "$EXIT_CODE" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

exit 0
