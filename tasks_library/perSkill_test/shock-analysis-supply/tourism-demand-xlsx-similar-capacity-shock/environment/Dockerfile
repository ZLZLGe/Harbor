FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    libreoffice \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

COPY tourism-capacity-template.xlsx /root/tourism-capacity-template.xlsx

RUN pip3 install --break-system-packages openpyxl==3.1.5

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills
