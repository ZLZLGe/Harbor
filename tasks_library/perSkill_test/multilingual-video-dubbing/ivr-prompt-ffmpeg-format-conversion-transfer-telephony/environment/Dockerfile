FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    ffmpeg \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

COPY voice_seed.mp4 /tmp/voice_seed.mp4
COPY skills /root/.codex/skills

RUN ffmpeg -y -v error -i /tmp/voice_seed.mp4 \
    -vn \
    -ac 1 \
    -ar 48000 \
    -c:a pcm_s16le \
    /root/ivr_prompt_master.wav

RUN mkdir -p /outputs /logs/verifier
