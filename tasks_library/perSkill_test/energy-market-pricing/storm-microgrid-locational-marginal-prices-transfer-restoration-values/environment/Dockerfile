FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pytest \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

COPY microgrid_assets.json /root/microgrid_assets.json
COPY repair_plan.json /root/repair_plan.json
COPY skills /root/.codex/skills
