#!/bin/bash
set -euo pipefail

pip3 install --break-system-packages \
    pytest==8.4.1 \
    pytest-json-ctrf==0.3.5 \
    pandas==2.2.2 \
    pyyaml==6.0.1 \
    numpy==1.26.4

TEST_FILE="$(dirname "$0")/test_outputs.py"

cd /root
if [ -f /root/gap_assist.py ]; then
    python3 /root/gap_assist.py
fi

set +e
pytest "$TEST_FILE" \
    --ctrf=/logs/verifier/ctrf.json \
    -v
exit_code=$?
set -e

if [ $exit_code -eq 0 ]; then
    echo "1" > /logs/verifier/reward.txt
else
    echo "0" > /logs/verifier/reward.txt
fi

exit $exit_code
