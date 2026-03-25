FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    curl \
    python3 \
    python3-numpy \
    python3-pytest \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean

WORKDIR /root

RUN mkdir -p /root/data /root/output

RUN npm init -y && npm install three@0.170.0

COPY data/assembly_scene.js /root/data/assembly_scene.js
COPY skills /root/.codex/skills
