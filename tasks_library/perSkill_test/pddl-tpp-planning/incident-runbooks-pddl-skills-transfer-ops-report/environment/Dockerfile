FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install \
    pytest==8.4.1 \
    pyperplan==2.1 \
    unified_planning==1.3.0 \
    up-pyperplan==1.1.0 \
    pyyaml==6.0.3

COPY runbooks /app/runbooks
COPY skills /app/skills
COPY skills /root/.codex/skills
