FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /root

RUN pip install --no-cache-dir pandas==2.2.3 rapidfuzz==3.14.0 pytest==8.3.3

COPY data /root/data
COPY data/2025-q2 /root/2025-q2
COPY data/2025-q3 /root/2025-q3

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills
