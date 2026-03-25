FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /root

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --no-cache-dir --break-system-packages --ignore-installed -U pip setuptools wheel

RUN python3 -m pip install --no-cache-dir --break-system-packages \
    numpy==2.2.6 \
    opencv-python-headless==4.12.0.88 \
    pytest==8.1.1

COPY crosswalk_drive.mp4 /root/crosswalk_drive.mp4
COPY ego_lane_roi.json /root/ego_lane_roi.json
COPY skills /root/.codex/skills
