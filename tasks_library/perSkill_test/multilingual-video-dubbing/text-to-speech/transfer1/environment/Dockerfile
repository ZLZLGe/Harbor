FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    espeak-ng \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir pytest==8.4.1

WORKDIR /root

COPY cue.srt promo_text.txt target_language.txt /root/
COPY skills /root/.codex/skills

RUN ffmpeg -y -f lavfi -i sine=frequency=110:duration=8 -af volume=0.12 -ar 48000 -ac 1 /root/bed.wav
RUN mkdir -p /outputs/tts_segments /logs/verifier
