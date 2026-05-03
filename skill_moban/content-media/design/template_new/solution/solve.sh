#!/bin/bash
set -euo pipefail

SOLUTION_ROOT="${SOLUTION_ROOT:-/solution}"
DECK_DIR="${TASK_DECK_DIR:-/root/environment/deck}"
ANSWER_DIR="${TASK_ANSWER_DIR:-/root/answer}"

cp "${SOLUTION_ROOT}/fixed/build_briefing.py" "${DECK_DIR}/build_briefing.py"
chmod +x "${DECK_DIR}/build_briefing.py"
python3 "${DECK_DIR}/build_briefing.py" --output "${ANSWER_DIR}"
