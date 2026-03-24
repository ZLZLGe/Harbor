#!/bin/bash
set -euo pipefail

LOG_ROOT="${LOG_ROOT:-/logs}"
TEST_OUTPUTS_PATH="${TEST_OUTPUTS_PATH:-/tests/test_outputs.py}"
OUTPUT_JSON_PATH="${AGENT_VOICE_ROSTER_JSON:-/root/agent_voice_roster.json}"

mkdir -p "$LOG_ROOT/verifier" "$LOG_ROOT/agent"

set +e
python3 "$TEST_OUTPUTS_PATH"
TEST_EXIT_CODE=$?
set -e

cp "$OUTPUT_JSON_PATH" "$LOG_ROOT/verifier/agent_voice_roster.json" 2>/dev/null || true
python3 "$TEST_OUTPUTS_PATH" --score "$LOG_ROOT/verifier/score.json" || true

if [ "$TEST_EXIT_CODE" -eq 0 ]; then
  echo 1 > "$LOG_ROOT/verifier/reward.txt"
else
  echo 0 > "$LOG_ROOT/verifier/reward.txt"
fi

exit "$TEST_EXIT_CODE"
