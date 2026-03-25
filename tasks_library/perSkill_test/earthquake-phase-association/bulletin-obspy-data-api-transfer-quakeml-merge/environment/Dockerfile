FROM python:3.11-slim

WORKDIR /root

RUN apt-get update && apt-get install -y --no-install-recommends \
    libxml2 \
    libxslt1.1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    obspy==1.4.2 \
    pandas==2.2.3 \
    pytest==8.3.4

COPY data /root/data
COPY skills /root/.codex/skills
