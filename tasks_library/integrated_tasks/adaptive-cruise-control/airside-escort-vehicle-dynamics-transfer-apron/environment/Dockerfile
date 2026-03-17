FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv

WORKDIR /root

RUN pip3 install --break-system-packages \
    pandas==2.2.2 \
    pyyaml==6.0.1

COPY apron_escort_config.yaml /root/apron_escort_config.yaml

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills
