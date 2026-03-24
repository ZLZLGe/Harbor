FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    poppler-utils \
    unzip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN mkdir -p /root/seminar_drop/inbox /root/seminar_drop/organized /root/seminar_drop/reports

COPY assets/ /root/seminar_drop/inbox/

# Copy skills to supported agent paths.
COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills

RUN pip3 install --break-system-packages \
    pytest==8.4.1 \
    PyPDF2==3.0.1
