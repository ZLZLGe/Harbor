FROM python:3.12-slim

WORKDIR /root

COPY data /root/data
COPY data/2025-q2 /root/2025-q2
COPY data/2025-q3 /root/2025-q3
COPY data/2025-q3/INFOTABLE.tsv /root/INFOTABLE.tsv

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills
