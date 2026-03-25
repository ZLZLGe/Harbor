FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-numpy \
    python3-pytest \
    python3-scipy \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

COPY redispatch_case.json /root/redispatch_case.json
COPY skills /root/.codex/skills
