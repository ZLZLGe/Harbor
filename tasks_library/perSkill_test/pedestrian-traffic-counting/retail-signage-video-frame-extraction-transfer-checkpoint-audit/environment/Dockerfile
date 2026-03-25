FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    python3 \
    python3-numpy \
    python3-opencv \
    python3-pil \
    python3-pytest \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN mkdir -p /app/input /app/output

COPY input /app/input
COPY skills /root/.codex/skills
