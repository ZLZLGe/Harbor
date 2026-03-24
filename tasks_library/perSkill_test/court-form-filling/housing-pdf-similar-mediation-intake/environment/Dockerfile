FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

RUN pip3 install --break-system-packages \
    pypdf==5.1.0 \
    reportlab==4.2.5

COPY generate_housing_form.py /tmp/generate_housing_form.py
RUN python3 /tmp/generate_housing_form.py /root/housing-mediation-intake.pdf

COPY dispute-summary.txt /root/dispute-summary.txt

# Copy skills to agent-specific locations
COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills
