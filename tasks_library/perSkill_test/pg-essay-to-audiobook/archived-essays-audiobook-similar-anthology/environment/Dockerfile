FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-bs4 \
    python3-pytest \
    ffmpeg \
    espeak-ng \
    && rm -rf /var/lib/apt/lists/*

COPY skills /root/.codex/skills
COPY archive_snapshots /root/archive_snapshots

WORKDIR /root
