FROM python:3.11-slim

WORKDIR /root

RUN apt-get update && apt-get install -y --no-install-recommends \
    libxml2 \
    libxslt1.1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    numpy==2.3.5 \
    obspy==1.4.1 \
    pandas==2.3.3 \
    pytest==8.4.1

COPY data /root/data
COPY skills /root/.codex/skills
