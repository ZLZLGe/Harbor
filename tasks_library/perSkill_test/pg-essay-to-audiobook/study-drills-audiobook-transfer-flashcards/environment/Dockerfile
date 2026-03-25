FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pytest \
    ffmpeg \
    espeak-ng

COPY skills /root/.codex/skills
COPY review_cards /root/review_cards

WORKDIR /root
