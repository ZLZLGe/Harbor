#!/bin/bash
set -u -o pipefail

mkdir -p /logs/verifier

set +e
python3 -m pytest -rA -v /tests/test_outputs.py | tee /logs/verifier/test_output.log
exit_code=${PIPESTATUS[0]}
set -e

if [ "$exit_code" -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi

exit 0
