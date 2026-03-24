FROM python:3.12-slim

USER root

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
  && rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.local/bin:$PATH"
ENV UV_CACHE_DIR="/tmp/uv-cache"
ENV UV_PYTHON_INSTALL_DIR="/tmp/uv-python"
RUN curl -LsSf https://astral.sh/uv/0.9.22/install.sh | sh

COPY repo /workspace/dev-bootstrap-station

# Copy skills to agent-specific locations
COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills

WORKDIR /workspace/dev-bootstrap-station
