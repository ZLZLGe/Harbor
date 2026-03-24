FROM python:3.12.9-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

COPY lead_batch.jsonl /root/lead_batch.jsonl
COPY prioritization_rules.json /root/prioritization_rules.json

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills
COPY skills /etc/claude-code/.claude/skills

RUN pip3 install --break-system-packages \
    rdkit==2025.09.3

ENV PYTHONUNBUFFERED=1
