FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pytest \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

COPY capture_feature_matrix.json /root/capture_feature_matrix.json

COPY skills /root/.codex/skills
