FROM python:3.12-slim

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skills
COPY skills /root/.agents/skills
COPY skills /root/.factory/skills
COPY skills /root/.goose/skills
COPY skills /root/.gemini/skills

COPY vendor /usr/local/lib/python3.12/site-packages
COPY training_program_input.xlsx /root/training_program_input.xlsx

WORKDIR /root
