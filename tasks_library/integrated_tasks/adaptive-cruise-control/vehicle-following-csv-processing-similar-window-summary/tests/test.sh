#!/bin/bash

pip3 install --break-system-packages \
    pytest==8.4.1 \
    pytest-json-ctrf==0.3.5 \
    pandas==2.2.2

TEST_FILE=$(find / -name "test_outputs.py" 2>/dev/null | head -1)

if [ -z "$TEST_FILE" ]; then
    echo "ERROR: Could not find test_outputs.py"
    echo "0" > /logs/verifier/reward.txt
    exit 1
fi

cd /root
if [ -f /root/summarize_following_windows.py ]; then
    python3 /root/summarize_following_windows.py
fi

pytest "$TEST_FILE" \
    --ctrf=/logs/verifier/ctrf.json \
    -v 2>&1

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo "1" > /logs/verifier/reward.txt
else
    echo "0" > /logs/verifier/reward.txt
fi

cp /root/*.py /logs/verifier/ 2>/dev/null || true
cp /root/*.csv /logs/verifier/ 2>/dev/null || true

exit 0
