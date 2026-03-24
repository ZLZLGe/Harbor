#!/bin/bash

mkdir -p /logs/verifier

pip3 install --break-system-packages \
    pytest==8.4.1 \
    numpy==1.26.4

cd /root
pytest /tests/test_outputs.py \
    --junitxml /logs/verifier/junit.xml \
    -v \
    -rA \
    2>&1
TEST_EXIT_CODE=$?

if [ "$TEST_EXIT_CODE" -eq 0 ]; then
    echo "1" > /logs/verifier/reward.txt
else
    echo "0" > /logs/verifier/reward.txt
fi

cp /root/fermentation_model_fit.json /logs/verifier/ 2>/dev/null || true

exit 0
