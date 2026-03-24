FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir \
    openpyxl==3.1.5 \
    pandas==2.2.3

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skills
COPY skills /root/.agents/skills
COPY skills /root/.factory/skills
COPY skills /root/.goose/skills
COPY skills /root/.gemini/skills

COPY warehouse_inventory.xlsx /root/warehouse_inventory.xlsx
COPY restock_rules.xlsx /root/restock_rules.xlsx

WORKDIR /root
