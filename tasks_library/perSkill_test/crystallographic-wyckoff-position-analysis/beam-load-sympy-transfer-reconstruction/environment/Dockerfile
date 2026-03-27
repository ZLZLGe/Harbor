# Dockerfile for Beam Load Integral Reconstruction
FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir \
    sympy==1.14.0

RUN mkdir -p /root/workspace /root/data

COPY beam_cases.json /root/data/

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
# Required for Harbor
# codex-hide-skill COPY skills /etc/claude-code/.claude/skills

WORKDIR /root

CMD ["/bin/bash"]
