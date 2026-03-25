FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /root

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --no-cache-dir --break-system-packages \
    pytest==8.1.1

COPY robot_patrol.mp4 /root/robot_patrol.mp4
COPY patrol_manifest.json /root/patrol_manifest.json
COPY robot_event_log.csv /root/robot_event_log.csv
COPY skills /root/.codex/skills
