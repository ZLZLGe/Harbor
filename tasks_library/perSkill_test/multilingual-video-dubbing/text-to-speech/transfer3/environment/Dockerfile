FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    espeak-ng \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir pytest==8.4.1

WORKDIR /root

COPY window.json narration.txt target_language.txt /root/
COPY skills /root/.codex/skills

RUN ffmpeg -y -f lavfi -i sine=frequency=330:duration=10 -af volume=0.08 -ar 48000 -ac 1 /root/ambient.wav
RUN mkdir -p /outputs/tts_segments /logs/verifier
