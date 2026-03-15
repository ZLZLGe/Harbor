FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    libreoffice \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

COPY vendor_catalog_archive.pdf /root/vendor_catalog_archive.pdf
COPY vendor_pricebook_current.xlsx /root/vendor_pricebook_current.xlsx

# Copy skills to agent-specific locations
COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills

RUN pip3 install --break-system-packages \
    openpyxl==3.1.5 \
    pandas==2.2.3 \
    pdfplumber==0.11.4
