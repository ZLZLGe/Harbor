FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    espeak-ng \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir pytest==8.4.1

WORKDIR /root

COPY segments.srt reference_target_text.srt target_language.txt /root/
COPY skills /root/.codex/skills

RUN ffmpeg -y \
    -f lavfi -i color=c=black:s=640x360:d=6:r=25 \
    -f lavfi -i sine=frequency=220:duration=6 \
    -c:v libx264 -pix_fmt yuv420p -c:a aac -ar 48000 -ac 1 /root/input.mp4

RUN mkdir -p /outputs/tts_segments /logs/verifier
