FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      python3 \
      python3-pip; \
    rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages \
    numpy==2.2.6 \
    pandas==2.3.2 \
    pillow==11.1.0 \
    scikit-image==0.25.2 \
    opencv-python-headless==4.11.0.86 \
    tifffile==2025.3.30

COPY workspace /app/workspace
WORKDIR /app/workspace

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills
