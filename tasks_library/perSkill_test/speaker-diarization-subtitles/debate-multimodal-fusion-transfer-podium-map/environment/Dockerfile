FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app/workspace

RUN pip install --no-cache-dir pytest==8.4.1

COPY speech_segments.csv /root/speech_segments.csv
COPY podium_motion_windows.json /root/podium_motion_windows.json
COPY cluster_slot_affinity.json /root/cluster_slot_affinity.json
COPY stage_layout.json /root/stage_layout.json
COPY skills /root/.codex/skills
