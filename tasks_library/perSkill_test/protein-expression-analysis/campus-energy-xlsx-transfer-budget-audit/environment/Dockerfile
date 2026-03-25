FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    libreoffice \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

COPY data/energy_budget_audit.xlsx /root/energy_budget_audit.xlsx
COPY skills /root/.codex/skills

RUN pip3 install --no-cache-dir --break-system-packages \
    openpyxl==3.1.5 \
    pytest==8.3.5
