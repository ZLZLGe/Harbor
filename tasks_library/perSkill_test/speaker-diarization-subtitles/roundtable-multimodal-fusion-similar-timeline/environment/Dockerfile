FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app/workspace

RUN pip install --no-cache-dir pytest==8.4.1

COPY audio_turn_candidates.json /root/audio_turn_candidates.json
COPY visual_windows.json /root/visual_windows.json
COPY cluster_face_affinity.json /root/cluster_face_affinity.json
COPY speaker_roster.json /root/speaker_roster.json

COPY skills /root/.codex/skills
