FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    espeak-ng \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir pytest==8.4.1

WORKDIR /root

COPY prompts.json target_language.txt /root/
COPY skills /root/.codex/skills

RUN mkdir -p /outputs/prompts /logs/verifier
