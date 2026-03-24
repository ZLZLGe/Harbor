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

COPY cell_migration_observations.json /root/cell_migration_observations.json
COPY cell_migration_dense_masks.npz /root/cell_migration_dense_masks.npz

COPY skills /root/.codex/skills
