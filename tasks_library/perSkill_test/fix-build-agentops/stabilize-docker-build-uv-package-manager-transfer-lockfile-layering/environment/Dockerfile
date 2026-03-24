# adapted from the source task's environment, but simplified for a standalone repo
FROM python:3.11-slim

USER root

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
  && rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.local/bin:$PATH"
ENV UV_CACHE_DIR="/tmp/uv-cache"
RUN curl -LsSf https://astral.sh/uv/0.9.22/install.sh | sh

COPY repo /workspace/incident-digest

# Copy skills to agent-specific locations
# Claude Code
COPY skills /root/.claude/skills
# Codex
COPY skills /root/.codex/skills
# OpenCode, NOTE: opencode use skill/ instead of skills/
COPY skills /root/.opencode/skill
# Goose
COPY skills /root/.goose/skills
# Factory
COPY skills /root/.factory/skills
# Goose/Amp (portable agents format)
COPY skills /root/.agents/skills
# Gemini
COPY skills /root/.gemini/skills

WORKDIR /workspace/incident-digest
