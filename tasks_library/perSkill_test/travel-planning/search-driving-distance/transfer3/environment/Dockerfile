FROM python:3.11-slim

RUN pip install --no-cache-dir pandas==2.0.3 numpy==1.24.3 requests==2.31.0

WORKDIR /root

COPY data /app/data
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
