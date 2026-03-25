FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages \
    numpy==2.3.3 \
    pytest==8.4.2

WORKDIR /root

COPY offshore_export_case.json /root/offshore_export_case.json
COPY skills /root/.codex/skills
