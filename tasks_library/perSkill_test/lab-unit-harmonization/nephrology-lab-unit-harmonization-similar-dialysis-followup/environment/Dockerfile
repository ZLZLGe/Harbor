FROM python:3.9.19-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    curl \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    numpy==1.24.3 \
    pandas==2.2.2 \
    pytest \
    pytest-json-ctrf

WORKDIR /root

COPY data /root/environment/data
COPY skills /root/environment/skills
COPY skills /root/.codex/skills
