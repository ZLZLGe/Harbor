FROM python:3.12-slim

WORKDIR /root

COPY energy_transfer_input.xlsx /root/energy_transfer_input.xlsx

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills

RUN pip install --no-cache-dir openpyxl==3.1.5
