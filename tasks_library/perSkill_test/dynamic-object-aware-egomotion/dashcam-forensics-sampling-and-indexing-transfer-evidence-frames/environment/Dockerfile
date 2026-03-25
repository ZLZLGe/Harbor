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
    numpy==1.26.4 \
    pillow==10.4.0 \
    pytest==8.1.1

COPY dashcam_clip.mp4 /root/dashcam_clip.mp4
COPY evidence_manifest.json /root/evidence_manifest.json
COPY incident_times.json /root/incident_times.json

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills
