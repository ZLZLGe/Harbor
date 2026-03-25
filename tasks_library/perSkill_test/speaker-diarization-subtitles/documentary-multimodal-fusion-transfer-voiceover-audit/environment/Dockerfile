FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app/workspace

RUN pip install --no-cache-dir pytest==8.4.1

COPY clip_manifest.json /root/clip_manifest.json
COPY speech_events.json /root/speech_events.json
COPY shot_observations.json /root/shot_observations.json
COPY skills /root/.codex/skills
