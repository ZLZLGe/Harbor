FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

RUN pip3 install --break-system-packages \
    pytest==8.4.1 \
    pandas==2.2.2 \
    pyyaml==6.0.1 \
    numpy==1.26.4

COPY greenhouse_policies.yaml /root/greenhouse_policies.yaml
COPY sensor_trace.csv /root/sensor_trace.csv

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills
