FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    poppler-utils \
    qpdf

WORKDIR /root

COPY assets /tmp/build_assets

# Copy skills to agent-specific locations
COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills

RUN pip3 install --break-system-packages \
    pypdf==5.9.0 \
    pdf2image==1.17.0 \
    pillow==11.1.0 \
    reportlab==4.2.5

RUN python3 /tmp/build_assets/build_form.py
