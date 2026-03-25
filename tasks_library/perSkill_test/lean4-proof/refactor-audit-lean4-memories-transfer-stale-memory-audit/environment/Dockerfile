FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
 && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir pytest==8.4.1 PyYAML==6.0.2

WORKDIR /app

COPY refactor_audit_inputs /app/refactor_audit_inputs
RUN mkdir -p /app/artifacts

COPY skills /root/.codex/skills
