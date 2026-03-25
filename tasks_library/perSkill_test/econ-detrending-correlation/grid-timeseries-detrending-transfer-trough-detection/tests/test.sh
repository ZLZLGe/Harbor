#!/bin/bash
set -u

mkdir -p /logs/verifier 2>/dev/null
if [ -d /logs/verifier ]; then
  LOG_DIR=/logs/verifier
else
  LOG_DIR="$(pwd)/.logs/verifier"
  mkdir -p "$LOG_DIR"
fi

python3 "$(dirname "$0")/test_outputs.py"
TEST_EXIT_CODE=$?

if [ "$TEST_EXIT_CODE" -eq 0 ]; then
  echo 1 > "$LOG_DIR/reward.txt"
else
  echo 0 > "$LOG_DIR/reward.txt"
fi

exit 0
