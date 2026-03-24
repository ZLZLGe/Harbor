#!/bin/bash

pip3 install --break-system-packages \
    pytest==8.4.1 \
    pytest-json-ctrf==0.3.5 \
    pandas==2.2.2 \
    pyyaml==6.0.1 \
    numpy==1.26.4

TEST_FILE="$(cd "$(dirname "$0")" && pwd)/test_outputs.py"

pytest "$TEST_FILE" --ctrf=/logs/verifier/ctrf.json -q
exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo "1" > /logs/verifier/reward.txt
else
    echo "0" > /logs/verifier/reward.txt
fi

exit 0
