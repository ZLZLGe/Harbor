#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier

if [ -f /root/auto-claim-filled.pdf ]; then
    cp /root/auto-claim-filled.pdf /logs/verifier/auto-claim-filled.pdf
fi

if [ -f /root/auto-claim-form.pdf ]; then
    cp /root/auto-claim-form.pdf /logs/verifier/auto-claim-form.pdf
fi

pip3 install --break-system-packages \
    pytest==8.4.1 \
    pytest-json-ctrf==0.3.5

set +e
pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA -v
PYTEST_EXIT_CODE=$?
set -e

if [ $PYTEST_EXIT_CODE -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi

exit 0
