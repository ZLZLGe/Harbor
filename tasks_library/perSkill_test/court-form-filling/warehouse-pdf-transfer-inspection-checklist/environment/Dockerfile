FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

COPY inspection-record.md /root/inspection-record.md
COPY generate_warehouse_checklist.py /root/generate_warehouse_checklist.py

RUN pip3 install --break-system-packages \
    pypdf==5.1.0 \
    reportlab==4.2.5 \
    pdfplumber==0.11.5 \
    pillow==11.1.0

RUN python3 /root/generate_warehouse_checklist.py /root/warehouse-inspection-checklist.pdf

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills
