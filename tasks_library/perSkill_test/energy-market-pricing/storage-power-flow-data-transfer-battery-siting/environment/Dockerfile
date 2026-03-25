FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pytest \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

COPY network.json /root/network.json
COPY candidate_sites.csv /root/candidate_sites.csv
COPY skills /root/.codex/skills
