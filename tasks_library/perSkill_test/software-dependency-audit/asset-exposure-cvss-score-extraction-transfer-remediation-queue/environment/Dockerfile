FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /root

COPY asset_exposure.csv /root/
COPY vulnerability_records.json /root/

# Copy skills to agent-specific locations
COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skills
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills
