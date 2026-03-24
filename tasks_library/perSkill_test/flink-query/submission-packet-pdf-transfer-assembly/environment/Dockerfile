FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    ca-certificates \
    curl \
    fonts-dejavu-core \
 && rm -rf /var/lib/apt/lists/*

COPY workspace /app/workspace
WORKDIR /app/workspace

# Copy skills to agent-specific locations
# Claude Code
COPY skills /root/.claude/skills
# Codex
COPY skills /root/.codex/skills
# OpenCode - singular "skill"
COPY skills /root/.opencode/skill
# Goose
COPY skills /root/.goose/skills
# Factory
COPY skills /root/.factory/skills
# Portable agents format (Goose, Amp)
COPY skills /root/.agents/skills
# Gemini
COPY skills /root/.gemini/skills

RUN python3 -m pip install --break-system-packages --no-cache-dir \
    pypdf==5.9.0 \
    reportlab==4.2.2 \
    pytest==8.4.1 \
    pytest-json-ctrf==0.3.5

RUN mkdir -p /app/artifacts
RUN python3 /app/workspace/input/generate_submission_inputs.py
