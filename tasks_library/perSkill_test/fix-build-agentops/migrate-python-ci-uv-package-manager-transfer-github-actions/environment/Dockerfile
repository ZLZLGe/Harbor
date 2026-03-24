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

COPY repo /workspace/scoreboard-service

# Copy skills to agent-specific locations
COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills

WORKDIR /workspace/scoreboard-service
