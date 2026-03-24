FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

COPY content_catalog.csv /root/content_catalog.csv
COPY rightsholder_master.csv /root/rightsholder_master.csv
COPY playback_log.csv /root/playback_log.csv
COPY royalty_splits.csv /root/royalty_splits.csv
COPY archive_manifest.csv /root/archive_manifest.csv
COPY 2025-q2 /root/2025-q2

# Copy skills to agent-specific locations
COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills

RUN pip3 install --break-system-packages pandas==2.3.3 rapidfuzz==3.14.3
