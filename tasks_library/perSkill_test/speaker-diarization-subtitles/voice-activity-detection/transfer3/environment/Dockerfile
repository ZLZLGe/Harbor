FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y python3 && rm -rf /var/lib/apt/lists/*

WORKDIR /app/workspace

COPY input.mp4 /root/input.mp4
COPY burst_activity.jsonl /root/burst_activity.jsonl
COPY audit_config.json /root/audit_config.json
COPY activity_cleanup.py /root/activity_cleanup.py

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills
