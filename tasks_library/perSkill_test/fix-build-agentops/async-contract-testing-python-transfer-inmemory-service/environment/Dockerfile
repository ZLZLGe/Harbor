FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
 && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --no-cache-dir --upgrade pip \
 && python -m pip install --no-cache-dir pytest==8.4.1 pytest-asyncio==0.24.0

COPY skills /root/.codex/skills

WORKDIR /workspace/dispatch-board
COPY project/ /workspace/dispatch-board/
