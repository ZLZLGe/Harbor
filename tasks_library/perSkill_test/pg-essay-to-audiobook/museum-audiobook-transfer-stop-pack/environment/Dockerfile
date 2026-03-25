FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PIP_BREAK_SYSTEM_PACKAGES=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    ffmpeg \
    espeak-ng \
    pocketsphinx \
    pocketsphinx-en-us \
    unzip \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --no-cache-dir pytest==8.4.1

COPY skills /root/.codex/skills
COPY exhibit_packet /root/exhibit_packet

WORKDIR /root
