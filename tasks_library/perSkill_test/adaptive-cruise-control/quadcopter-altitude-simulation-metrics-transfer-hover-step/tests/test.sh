#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier

set +e
pytest /tests/test_outputs.py -v 2>&1 | tee /logs/verifier/pytest.log
test_status=${PIPESTATUS[0]}
set -e

if [ "${test_status}" -eq 0 ]; then
    reward="1.0"
else
    reward="0.0"
fi

printf '%s\n' "${reward}" > /logs/verifier/reward.txt

exit "${test_status}"
