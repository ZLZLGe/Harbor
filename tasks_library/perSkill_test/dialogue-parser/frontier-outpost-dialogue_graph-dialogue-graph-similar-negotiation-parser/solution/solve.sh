#!/bin/bash
set -ex

cd /app || cd /root || true

export PYTHONPATH="$PYTHONPATH:/app/environment/skills/dialogue_graph/scripts:/root/.claude/skills/dialogue_graph/scripts:/root/.agents/skills/dialogue_graph/scripts"

python3 /solution/solution.py

echo "Solution completed. Checking output..."
ls -la /app/outpost_dialogue.json /app/outpost_dialogue.dot
