FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

COPY packet_page_order.txt /root/packet_page_order.txt
COPY create_board_packet_assets.py /tmp/create_board_packet_assets.py

# Copy skills to agent-specific locations
# Claude Code
COPY skills /root/.claude/skills
# Codex
COPY skills /root/.codex/skills
# OpenCode
COPY skills /root/.opencode/skill
# Goose
COPY skills /root/.goose/skills
# Factory
COPY skills /root/.factory/skills
# Portable agents format (Goose, Amp)
COPY skills /root/.agents/skills
# Gemini
COPY skills /root/.gemini/skills

RUN pip3 install --break-system-packages \
    pypdf==5.7.0 \
    reportlab==4.2.5

RUN python3 /tmp/create_board_packet_assets.py && rm /tmp/create_board_packet_assets.py
