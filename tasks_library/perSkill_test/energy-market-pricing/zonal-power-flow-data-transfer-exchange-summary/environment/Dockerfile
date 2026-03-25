FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    && python3 -m pip install --break-system-packages pytest==8.3.5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

COPY network.json /root/network.json
COPY zones.json /root/zones.json
COPY skills /root/.codex/skills
