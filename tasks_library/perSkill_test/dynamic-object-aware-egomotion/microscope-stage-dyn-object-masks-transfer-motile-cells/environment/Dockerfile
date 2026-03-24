FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /root

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    ffmpeg

RUN python3 -m pip install --no-cache-dir --break-system-packages --ignore-installed -U pip setuptools wheel

RUN python3 -m pip install --no-cache-dir --break-system-packages \
    numpy==1.26.4 \
    pytest==8.1.1

RUN python3 -m pip install --no-cache-dir --break-system-packages \
    --only-binary=:all: \
    opencv-python-headless==4.12.0.88

COPY microscope_frames /tmp/microscope_frames
RUN ffmpeg -y -framerate 12 -i /tmp/microscope_frames/frame_%04d.pgm \
    -c:v libx264 -pix_fmt yuv420p /root/microscope_stage_drift.mp4

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills
