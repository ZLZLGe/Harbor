FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /root

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    ffmpeg

RUN python3 -m pip install --break-system-packages --ignore-installed -U pip setuptools wheel
RUN python3 -m pip install --break-system-packages \
    numpy==1.26.4 \
    opencv-python-headless==4.10.0.84 \
    pytest==8.4.1

COPY build_input_video.py /root/build_input_video.py
RUN python3 /root/build_input_video.py

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills
