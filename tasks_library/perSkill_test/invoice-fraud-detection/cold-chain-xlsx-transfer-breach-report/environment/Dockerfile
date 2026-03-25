FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

COPY cold_chain_monitor_book /root/
COPY skills /root/.codex/skills

RUN pip3 install --break-system-packages \
    openpyxl==3.1.5 \
    pandas==2.3.3 \
    pytest==8.4.1
