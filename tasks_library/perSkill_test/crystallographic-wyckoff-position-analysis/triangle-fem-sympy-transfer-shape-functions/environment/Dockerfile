# Dockerfile for linear triangle FEM shape-function task
FROM python:3.12-slim

RUN pip3 install --no-cache-dir \
    sympy==1.14.0

RUN mkdir -p /root/workspace /root/triangle_cases

COPY triangle_cases.toml /root/triangle_cases/triangle_cases.toml

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
