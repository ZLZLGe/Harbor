FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    jq \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

COPY input /root/input

RUN pip3 install --break-system-packages \
    pytest==8.4.1 \
    pytest-json-ctrf==0.3.5 \
    pyyaml==6.0.2

# Copy skills to agent-specific locations. The without-skill runtime removes
# these COPY lines while keeping all task data, tests, and dependencies fixed.
COPY skills /root/.codex/skills
COPY skills /root/.claude/skills
COPY skills /root/.opencode/skill
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills
