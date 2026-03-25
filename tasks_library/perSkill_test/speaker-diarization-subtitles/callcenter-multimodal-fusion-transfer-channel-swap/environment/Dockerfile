FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app/workspace

RUN pip install --no-cache-dir pytest==8.4.1

COPY session_manifest.json /root/session_manifest.json
COPY audio_activity_windows.json /root/audio_activity_windows.json
COPY split_screen_observations.json /root/split_screen_observations.json
COPY skills /root/.codex/skills
