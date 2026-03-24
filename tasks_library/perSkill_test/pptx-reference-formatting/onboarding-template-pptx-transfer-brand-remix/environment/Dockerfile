FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages \
    lxml==5.3.0 \
    defusedxml==0.7.1 \
    six==1.17.0 \
    pillow==11.0.0 \
    python-pptx==0.6.23

WORKDIR /root
COPY Northstar-Brand-Template.pptx /root/
COPY onboarding-outline.md /root/

# Copy skills to ALL agent paths
COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills
