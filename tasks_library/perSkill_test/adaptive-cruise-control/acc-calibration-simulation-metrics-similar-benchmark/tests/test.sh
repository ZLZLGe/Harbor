#!/bin/bash
set -euo pipefail

pip3 install --break-system-packages \
    pytest==8.4.1 \
    pandas==2.2.2 \
    pyyaml==6.0.1 \
    numpy==1.26.4

TEST_DIR="$(cd "$(dirname "$0")" && pwd)"

set +e
pytest "$TEST_DIR/test_outputs.py" -q
exit_code=$?
set -e

if [ -d /logs/verifier ]; then
    if [ "$exit_code" -eq 0 ]; then
        echo "1" > /logs/verifier/reward.txt
    else
        echo "0" > /logs/verifier/reward.txt
    fi
fi

exit "$exit_code"
