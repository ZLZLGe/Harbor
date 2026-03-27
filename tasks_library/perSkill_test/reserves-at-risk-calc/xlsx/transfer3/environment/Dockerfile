
FROM python:3.12-slim

WORKDIR /root

COPY cold_chain_transfer3_input.xlsx /root/cold_chain_transfer3_input.xlsx

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills

RUN pip install --no-cache-dir openpyxl==3.1.5
