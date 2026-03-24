#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier

test_file=""
for candidate in \
    /tests/test_outputs.py \
    /root/tests/test_outputs.py \
    "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/test_outputs.py"
do
    if [ -f "$candidate" ]; then
        test_file="$candidate"
        break
    fi
done

set +e
if [ -n "$test_file" ]; then
    pytest -q "$test_file" > /logs/verifier/pytest.log 2>&1
    test_status=$?
else
    echo "ERROR: file or directory not found: test_outputs.py" > /logs/verifier/pytest.log
    test_status=1
fi
set -e

cat /logs/verifier/pytest.log

if [ "$test_status" -eq 0 ]; then
    printf '1.0\n' > /logs/verifier/reward.txt
else
    printf '0.0\n' > /logs/verifier/reward.txt
fi

exit "$test_status"
