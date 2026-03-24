#!/bin/bash
set -ex

cd /app || cd /root || true

export PYTHONPATH="$PYTHONPATH:/app/environment/skills/dialogue_graph/scripts:/root/.codex/skills/dialogue_graph/scripts:/root/.claude/skills/dialogue_graph/scripts"

python3 /solution/solution.py

ls -la /app/warranty_returns_flow.json /app/warranty_returns_flow.dot
