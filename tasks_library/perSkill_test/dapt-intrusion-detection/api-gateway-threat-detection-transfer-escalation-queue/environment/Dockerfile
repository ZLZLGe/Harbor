FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir pytest==8.4.1

WORKDIR /root

COPY gateway_tenant_profiles.tsv /root/gateway_tenant_profiles.tsv
COPY skills /root/.codex/skills
