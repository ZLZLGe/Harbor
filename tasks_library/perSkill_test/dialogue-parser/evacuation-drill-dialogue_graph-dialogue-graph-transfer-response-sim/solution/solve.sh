#!/bin/bash
set -ex

cd /app || cd /root || true

export PYTHONPATH="$PYTHONPATH:/app/environment/skills/dialogue_graph/scripts:/root/.claude/skills/dialogue_graph/scripts:/root/.agents/skills/dialogue_graph/scripts"

if [ -f /solution/solution.py ]; then
    python3 /solution/solution.py
else
    python3 solution/solution.py
fi

echo "Solution completed. Checking output..."
ls -la /app/evacuation_response.json /app/evacuation_response.dot
