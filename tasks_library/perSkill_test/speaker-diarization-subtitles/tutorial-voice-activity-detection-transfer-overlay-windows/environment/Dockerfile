FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    pytest==8.4.1 \
    webrtcvad==2.0.10

WORKDIR /app/workspace

COPY tutorial_walkthrough.mp4 /root/tutorial_walkthrough.mp4
COPY overlay_policy.json /root/overlay_policy.json
COPY skills /root/.codex/skills
