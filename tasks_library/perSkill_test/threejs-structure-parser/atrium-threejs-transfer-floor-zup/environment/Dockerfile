FROM node:22-bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pytest \
    python3-numpy \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

RUN mkdir -p /root/data /root/output /root/.codex
RUN npm init -y && npm install three@0.170.0

COPY data/atrium_scene.js /root/data/atrium_scene.js
COPY skills /root/.codex/skills
