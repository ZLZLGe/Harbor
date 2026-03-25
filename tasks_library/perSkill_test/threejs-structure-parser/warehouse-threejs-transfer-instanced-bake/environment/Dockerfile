FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    ca-certificates \
    nodejs \
    npm \
    python3 \
    python3-numpy \
    python3-pytest \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

RUN mkdir -p /root/data /root/output

RUN npm init -y \
    && npm pkg set type=module \
    && npm install three@0.170.0

COPY data/warehouse_scene.js /root/data/warehouse_scene.js
COPY skills /root/.codex/skills
