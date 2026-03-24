FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    libreoffice \
    gnumeric \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

COPY data/metabolite_treatment_shift_scorecard.xlsx /root/metabolite_treatment_shift_scorecard.xlsx

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.github/skills
COPY skills /root/.gemini/skills

RUN pip3 install --no-cache-dir --break-system-packages \
    openpyxl==3.1.5
