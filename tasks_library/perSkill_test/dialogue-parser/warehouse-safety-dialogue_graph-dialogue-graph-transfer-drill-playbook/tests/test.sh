#!/bin/bash
set -euo pipefail

pip3 install --break-system-packages pytest==8.3.4 pytest-json-ctrf==0.3.6
mkdir -p /logs/verifier
export PYTHONPATH="$PYTHONPATH:/app/environment/skills/dialogue_graph/scripts"

pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA -v 2>&1 | tee /logs/verifier/pytest_output.txt
RESULT=${PIPESTATUS[0]}

if [ -f /logs/verifier/ctrf.json ]; then
    PASSED=$(python3 -c "import json; d=json.load(open('/logs/verifier/ctrf.json')); print(d['results']['summary']['passed'])" 2>/dev/null || echo 0)
    TOTAL=$(python3 -c "import json; d=json.load(open('/logs/verifier/ctrf.json')); print(d['results']['summary']['tests'])" 2>/dev/null || echo 1)
    if [ "$TOTAL" -gt 0 ]; then
        SCORE=$(python3 -c "print(round($PASSED / $TOTAL, 3))")
    else
        SCORE=0
    fi
    echo "$SCORE" > /logs/verifier/reward.txt
else
    echo "0" > /logs/verifier/reward.txt
fi

exit "$RESULT"
