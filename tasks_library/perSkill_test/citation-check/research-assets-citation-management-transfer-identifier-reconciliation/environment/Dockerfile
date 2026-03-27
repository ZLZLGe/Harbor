FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    wget \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

RUN pip3 install --break-system-packages \
    requests==2.32.3

COPY research_assets.txt /root/research_assets.txt
COPY record_snapshot.json /root/record_snapshot.json

# Copy skills to agent-specific locations
# Claude Code
# codex-hide-skill COPY skills /root/.claude/skills
# Codex
# codex-hide-skill COPY skills /root/.codex/skills
# OpenCode
# codex-hide-skill COPY skills /root/.opencode/skill
# Goose
# codex-hide-skill COPY skills /root/.goose/skills
# Factory
# codex-hide-skill COPY skills /root/.factory/skills
# Portable agents format (Goose, Amp)
# codex-hide-skill COPY skills /root/.agents/skills
# Gemini
# codex-hide-skill COPY skills /root/.gemini/skills
