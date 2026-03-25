FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages \
    openai==2.15.0 \
    pytest==8.4.1

RUN mkdir -p /app/input /app/output
COPY input /app/input

WORKDIR /app

COPY skills /root/.codex/skills
