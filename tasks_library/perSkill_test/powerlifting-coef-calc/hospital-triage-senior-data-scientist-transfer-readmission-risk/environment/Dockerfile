FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    libreoffice \
    gnumeric \
    curl \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.local/bin:$PATH"
RUN mkdir -p /usr/local/bin
RUN curl -LsSf https://astral.sh/uv/0.9.22/install.sh | env UV_INSTALL_DIR="/usr/local/bin" sh

WORKDIR /root

RUN mkdir -p /root/data
COPY readmission_risk_dashboard.xlsx /root/data/readmission_risk_dashboard.xlsx
COPY readmission-readme.md /root/data/readmission-readme.md

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills
