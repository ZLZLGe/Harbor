FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    nodejs \
    npm \
    python3 \
    python3-numpy \
    python3-pytest \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

RUN mkdir -p /root/data /root/output

RUN npm init -y \
    && npm pkg set type=module \
    && npm install three@0.175.0

COPY data/display_scene.js /root/data/display_scene.js
COPY skills /root/.codex/skills
