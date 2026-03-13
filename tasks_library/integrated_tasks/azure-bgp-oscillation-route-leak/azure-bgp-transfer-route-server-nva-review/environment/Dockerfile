FROM python:3.11-slim

RUN mkdir -p /app/data /app/output /app/environment/data

COPY data /app/environment/data

RUN python3 << 'DATAGEN'
import json
from pathlib import Path

data_root = Path("/app/environment/data")
app_data = Path("/app/data")
app_data.mkdir(parents=True, exist_ok=True)

with open(data_root / "route_server_incident.json", "r", encoding="utf-8") as f:
    scenario = json.load(f)

file_map = {
    "topology": "topology.json",
    "sessions": "sessions.json",
    "preferences": "preferences.json",
    "relationships": "relationships.json",
    "local_pref": "local_pref.json",
    "review_context": "review_context.json",
    "route_events": "route_events.json",
    "possible_actions": "possible_actions.json",
}

for key, filename in file_map.items():
    with open(app_data / filename, "w", encoding="utf-8") as f:
        json.dump(scenario[key], f, indent=2)

print("Generated Azure Route Server NVA review inputs in /app/data")
DATAGEN

WORKDIR /app

COPY skills /root/.claude/skills
COPY skills /etc/claude-code/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills
