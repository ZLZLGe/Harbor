FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

RUN pip3 install --break-system-packages \
    numpy==1.26.4 \
    pandas==2.2.2 \
    pyyaml==6.0.1

COPY furnace_temperature_runs.csv /root/furnace_temperature_runs.csv
COPY furnace_benchmark.yaml /root/furnace_benchmark.yaml

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills
