FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

COPY create_vendor_inputs.py /tmp/create_vendor_inputs.py
RUN python3 /tmp/create_vendor_inputs.py && rm /tmp/create_vendor_inputs.py

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
