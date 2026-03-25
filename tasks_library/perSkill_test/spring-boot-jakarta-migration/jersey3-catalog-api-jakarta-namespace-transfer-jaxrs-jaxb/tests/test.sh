#!/bin/bash

set -u

mkdir -p /logs/verifier

python3 -m pytest /tests/test_outputs.py -rA -v 2>&1 | tee /logs/verifier/test_output.log
exit_code=${PIPESTATUS[0]}

if [ "$exit_code" -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi

exit 0
