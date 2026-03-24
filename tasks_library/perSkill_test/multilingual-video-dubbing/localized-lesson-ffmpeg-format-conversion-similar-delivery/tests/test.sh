#!/bin/bash
set -euo pipefail

pip3 install --break-system-packages -q pytest==9.0.2 pytest-json-ctrf==0.3.6 numpy==1.26.4

mkdir -p /logs/verifier

pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA -v
PYTEST_EXIT_CODE=$?

if [ -f "/outputs/localized_lesson.mp4" ]; then
  cp /outputs/localized_lesson.mp4 /logs/verifier/localized_lesson.mp4
fi

if [ $PYTEST_EXIT_CODE -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

exit 0
