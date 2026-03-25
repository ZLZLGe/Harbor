FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
 && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --no-cache-dir --upgrade pip \
 && python -m pip install --no-cache-dir pytest==8.3.5

COPY skills /root/.codex/skills

WORKDIR /workspace/shift-digest
COPY project/ /workspace/shift-digest/
