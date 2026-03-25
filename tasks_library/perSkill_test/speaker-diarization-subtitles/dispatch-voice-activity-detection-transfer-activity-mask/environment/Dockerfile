FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN pip install --no-cache-dir \
    pytest==8.4.1

WORKDIR /app/workspace

COPY dispatch_recording.wav /root/dispatch_recording.wav
COPY mask_policy.json /root/mask_policy.json
COPY skills /root/.codex/skills
