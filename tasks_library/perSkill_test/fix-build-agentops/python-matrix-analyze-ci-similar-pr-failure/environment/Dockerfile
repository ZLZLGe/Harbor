# local Python PR matrix fixture
FROM python:3.11-slim

USER root

RUN apt-get update && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        curl \
        git \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.local/bin:$PATH"
RUN curl -LsSf https://astral.sh/uv/0.9.22/install.sh | sh

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

COPY repo /workspace/repo
COPY ci_artifacts /workspace/ci_artifacts

RUN mkdir -p /workspace/reports \
    && chmod +x /workspace/repo/scripts/run_pr_matrix.sh

WORKDIR /workspace/repo
