FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /root

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --no-cache-dir --break-system-packages \
    numpy==1.26.4 \
    pytest==8.4.1

COPY conference_manifest.json /root/conference_manifest.json
COPY room_seat_map.csv /root/room_seat_map.csv
COPY meeting_schedule.json /root/meeting_schedule.json
COPY checkin_log.csv /root/checkin_log.csv

COPY skills /root/.codex/skills
