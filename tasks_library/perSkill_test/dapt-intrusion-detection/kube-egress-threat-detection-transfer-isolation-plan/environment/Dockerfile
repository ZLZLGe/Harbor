FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    pytest==8.4.1 \
    PyYAML==6.0.2

WORKDIR /root

COPY pod_egress_profiles.jsonl /root/pod_egress_profiles.jsonl
COPY skills /root/.codex/skills
