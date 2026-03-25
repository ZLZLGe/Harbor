FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir pytest==8.4.1

WORKDIR /app

COPY session_assets /app/session_assets

# Copy skills to agent-specific locations
# Claude Code
COPY skills /root/.claude/skills
# Codex
COPY skills /root/.codex/skills
# OpenCode
COPY skills /root/.opencode/skill
# Goose
COPY skills /root/.goose/skills
# Factory
COPY skills /root/.factory/skills
# Portable agents format (Goose, Amp)
COPY skills /root/.agents/skills
# Gemini
COPY skills /root/.gemini/skills
