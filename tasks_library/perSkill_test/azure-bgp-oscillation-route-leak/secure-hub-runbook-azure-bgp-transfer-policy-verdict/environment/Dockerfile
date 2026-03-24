FROM python:3.11-slim

RUN mkdir -p /app/data /app/output /app/environment/data

COPY data /app/environment/data

RUN python <<'PY'
import json
from pathlib import Path

src = Path("/app/environment/data")
dst = Path("/app/data")
dst.mkdir(parents=True, exist_ok=True)

for path in sorted(src.glob("*.json")):
    json.loads(path.read_text())
    (dst / path.name).write_text(path.read_text())
PY

WORKDIR /app

COPY skills /root/.claude/skills
COPY skills /etc/claude-code/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills
