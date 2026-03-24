#!/bin/bash
set -ex

if [ -d /app ]; then
    cd /app
fi

export PYTHONPATH="$PYTHONPATH:/app/environment/skills/dialogue_graph/scripts:/root/.claude/skills/dialogue_graph/scripts"

python3 /solution/solution.py

ls -la museum_audio_route.json museum_audio_route.dot
