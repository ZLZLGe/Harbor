# local docs build fixture
FROM node:22-bullseye-slim

USER root

RUN apt-get update && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        curl \
        git \
        python3 \
    && rm -rf /var/lib/apt/lists/*

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
    && chmod +x /workspace/repo/scripts/run_docs_ci.sh

WORKDIR /workspace/repo
