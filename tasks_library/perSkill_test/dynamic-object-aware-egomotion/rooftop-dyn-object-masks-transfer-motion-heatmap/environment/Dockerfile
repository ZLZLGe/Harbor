FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /root

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --no-cache-dir --break-system-packages \
    numpy==1.26.4 \
    opencv-python-headless==4.10.0.84 \
    pytest==8.1.1

COPY rooftop_inspection.y4m /root/rooftop_inspection.y4m
COPY heatmap_spec.json /root/heatmap_spec.json
COPY skills /root/.codex/skills
