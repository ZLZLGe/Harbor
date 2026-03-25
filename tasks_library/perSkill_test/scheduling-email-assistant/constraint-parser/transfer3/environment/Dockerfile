FROM python:3.11-slim

WORKDIR /root

COPY data /root/data
COPY skills /app/skills

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills

ENV PYTHONUNBUFFERED=1
