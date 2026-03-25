FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    numpy==2.1.1 \
    pandas==2.2.3 \
    pytest==8.4.1 \
    pytest-json-ctrf==0.3.5

WORKDIR /root

COPY data /root/data

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills
