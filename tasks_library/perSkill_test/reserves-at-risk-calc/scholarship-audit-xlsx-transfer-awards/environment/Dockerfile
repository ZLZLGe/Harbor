FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    libreoffice \
    gnumeric \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root
RUN mkdir -p /root/data /root/output

COPY scholarship-audit-template.xlsx /root/data/scholarship-audit-template.xlsx

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills

RUN pip3 install --break-system-packages \
    openpyxl==3.1.5 \
    pytest==8.4.1
