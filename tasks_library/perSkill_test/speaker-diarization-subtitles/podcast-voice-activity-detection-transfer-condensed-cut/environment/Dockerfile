FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    pytest==8.4.1

WORKDIR /app/workspace

COPY raw_podcast.wav /root/raw_podcast.wav
COPY edit_policy.json /root/edit_policy.json
COPY skills /root/.codex/skills
