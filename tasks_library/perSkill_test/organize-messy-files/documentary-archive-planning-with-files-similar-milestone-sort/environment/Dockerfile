FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    poppler-utils \
    unzip \
    zip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

COPY build_assets.py /tmp/build_assets.py

RUN mkdir -p /root/documentary_archive/inbox /root/reports \
    && python3 /tmp/build_assets.py \
    && rm /tmp/build_assets.py

# Copy skills to ALL agent paths
COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills
