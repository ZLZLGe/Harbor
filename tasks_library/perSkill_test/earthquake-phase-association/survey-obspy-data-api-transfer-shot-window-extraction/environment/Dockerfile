FROM python:3.11-slim

WORKDIR /root

RUN apt-get update && apt-get install -y --no-install-recommends \
    libxml2 \
    libxslt1.1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    obspy==1.4.1 \
    pytest==8.3.5

COPY data /root/data
COPY skills /root/.codex/skills
