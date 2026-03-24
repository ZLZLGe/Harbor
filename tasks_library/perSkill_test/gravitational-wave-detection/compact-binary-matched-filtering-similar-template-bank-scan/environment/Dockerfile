FROM python:3.9.19-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    gcc \
    g++ \
    git \
    libblas-dev \
    libffi-dev \
    libhdf5-dev \
    liblapack-dev \
    libssl-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    pycbc==2.8.5 \
    pandas==2.2.2 \
    pytest==8.4.1 \
    pytest-json-ctrf==0.3.5

WORKDIR /root

COPY data /root/data
COPY skills /root/.codex/skills
