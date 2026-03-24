#!/bin/bash

mkdir -p /logs/verifier

pip3 install --break-system-packages \
    pytest==8.4.1 \
    pytest-json-ctrf==0.3.5

cd /root
pytest /tests/test_outputs.py \
    --ctrf /logs/verifier/ctrf-report.json \
    -v \
    -rA \
    2>&1
TEST_EXIT_CODE=$?

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "1" > /logs/verifier/reward.txt
else
    echo "0" > /logs/verifier/reward.txt
fi

cp /root/startup_safety_report.json /logs/verifier/ 2>/dev/null || true

exit 0
