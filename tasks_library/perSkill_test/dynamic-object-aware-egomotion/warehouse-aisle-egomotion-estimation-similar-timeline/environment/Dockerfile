FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /root

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    numpy==1.26.4 \
    opencv-python-headless==4.10.0.84 \
    pytest==8.1.1

COPY warehouse_patrol.mp4 /root/warehouse_patrol.mp4
COPY run_manifest.json /root/run_manifest.json
COPY skills /root/.codex/skills
