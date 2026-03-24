FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    libreoffice \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

COPY create_workbooks.py /tmp/create_workbooks.py
RUN python3 /tmp/create_workbooks.py

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

RUN pip3 install --break-system-packages \
    openpyxl==3.1.5 \
    pandas==2.2.3
