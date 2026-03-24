FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    ffmpeg \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

COPY lobby_camera.mp4 redaction_schedule.json /root/
COPY skills /root/.codex/skills

RUN mkdir -p /outputs /logs/verifier
