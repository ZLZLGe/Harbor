FROM node:20-bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    && python3 -m pip install --break-system-packages --no-cache-dir \
    numpy==2.1.3 \
    pytest==8.4.1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

RUN mkdir -p /root/data /root/output

RUN npm init -y \
    && npm pkg set type=module \
    && npm install three@0.175.0

COPY data/wayfinding_scene.js /root/data/wayfinding_scene.js
COPY skills /root/.codex/skills
