FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /root

COPY release_candidate_snapshot.json /root/
COPY release_gate_policy.json /root/

# Copy skills to agent-specific locations
# Claude Code
COPY skills /root/.claude/skills
# Codex
COPY skills /root/.codex/skills
# OpenCode
COPY skills /root/.opencode/skills
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
# Goose/Amp (portable agents format)
COPY skills /root/.agents/skills
# Gemini
COPY skills /root/.gemini/skills
