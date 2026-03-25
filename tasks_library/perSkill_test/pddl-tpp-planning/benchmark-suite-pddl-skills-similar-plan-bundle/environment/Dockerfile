FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    pyperplan==2.1 \
    pytest==8.4.1 \
    unified-planning==1.3.0 \
    up-pyperplan==1.1.0

COPY benchmark /app/benchmark
COPY skills /app/skills
COPY skills /root/.codex/skills
