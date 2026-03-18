# Dockerfile for Batch Symmetry Fingerprint Report Task
FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir \
    pymatgen==2025.10.7

RUN mkdir -p /root/workspace /root/structures

COPY *.cif /root/structures/

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

WORKDIR /root

CMD ["/bin/bash"]
