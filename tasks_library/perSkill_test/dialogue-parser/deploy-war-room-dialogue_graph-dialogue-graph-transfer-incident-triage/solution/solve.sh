#!/bin/bash
set -ex

cd /app || cd /root || true

export PYTHONPATH=$PYTHONPATH:/app/environment/skills/dialogue_graph/scripts:/root/.codex/skills/dialogue_graph/scripts:/root/.claude/skills/dialogue_graph/scripts:/root/.agents/skills/dialogue_graph/scripts

python3 /solution/solution.py

echo "Solution completed. Checking output..."
ls -la incident_triage_map.json incident_triage_map.dot
