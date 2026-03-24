FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    wget \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /app/loading_dock
COPY loading_dock /app/loading_dock
WORKDIR /app/loading_dock

# Copy skills to ALL agent paths
COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
# Gemini
COPY skills /root/.gemini/skills

RUN pip3 install --break-system-packages \
    google-genai==1.59.0
