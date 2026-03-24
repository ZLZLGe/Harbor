FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /root

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --no-cache-dir --break-system-packages --ignore-installed -U pip setuptools wheel

RUN python3 -m pip install --no-cache-dir --break-system-packages \
    numpy==1.26.4 \
    pytest==8.1.1

COPY wildfire_sampling_manifest.csv /root/wildfire_sampling_manifest.csv
COPY wildfire_fireline_runs.json /root/wildfire_fireline_runs.json

COPY skills /root/.codex/skills
