FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    pandas==2.2.3 \
    pytest==8.3.5

WORKDIR /root

COPY data /root/environment/data
COPY skills /root/environment/skills
COPY skills /root/.codex/skills
