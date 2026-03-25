FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-numpy \
    python3-pytest \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

COPY corridor_case.json /root/corridor_case.json
COPY skills /root/.codex/skills
