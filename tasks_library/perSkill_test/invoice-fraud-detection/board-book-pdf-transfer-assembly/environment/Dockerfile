FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

COPY board_packet_manifest.json /root/
COPY meeting_core.pdf /root/
COPY committee_updates.pdf /root/
COPY finance_appendix.pdf /root/
COPY strategy_exhibits.pdf /root/

# Copy skills to agent-specific locations
COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills

RUN pip3 install --break-system-packages \
    pypdf==6.6.0 \
    pdfplumber==0.11.9 \
    reportlab==4.4.7
