FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    unzip \
    zip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

COPY inbox /root/inbox

RUN mkdir -p \
    /root/desks/climate_transition \
    /root/desks/consumer_ai \
    /root/desks/public_health \
    /root/desks/urban_mobility

# Copy skills to ALL agent paths
COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills

RUN pip3 install --break-system-packages pytest==8.4.1
