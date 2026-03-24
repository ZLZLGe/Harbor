FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages \
    pymupdf==1.24.0 \
    pypdf==4.0.0

COPY build_manuscript_fixture.py /tmp/build_manuscript_fixture.py
RUN mkdir -p /root/submission && python3 /tmp/build_manuscript_fixture.py /root/submission/manuscript_packet.pdf

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

WORKDIR /root
