FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    ca-certificates \
    nodejs \
    npm \
    python3 \
    python3-pytest

WORKDIR /root

RUN mkdir -p /root/data /root/output /root/.codex/skills

RUN npm init -y >/dev/null 2>&1 \
    && npm install three@0.170.0

COPY data/ /root/data/
COPY skills /root/.codex/skills
