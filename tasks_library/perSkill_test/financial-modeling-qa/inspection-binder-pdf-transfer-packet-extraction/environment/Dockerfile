FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y python3 python3-pip \
  && pip3 install --break-system-packages pypdf==5.1.0 \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /root

COPY inspection_binder.pdf /root/inspection_binder.pdf

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills
COPY skills /root/.factory/skills
