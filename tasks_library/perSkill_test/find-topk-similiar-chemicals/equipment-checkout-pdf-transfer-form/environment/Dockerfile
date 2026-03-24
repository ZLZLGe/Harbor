FROM python:3.12.9-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

WORKDIR /root

COPY create_assets.py /tmp/create_assets.py

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
# Required for Harbor
COPY skills /etc/claude-code/.claude/skills

RUN pip3 install --break-system-packages \
    reportlab==4.2.2 \
    pdfplumber==0.11.9 \
    pypdf==6.6.0

RUN python3 /tmp/create_assets.py
