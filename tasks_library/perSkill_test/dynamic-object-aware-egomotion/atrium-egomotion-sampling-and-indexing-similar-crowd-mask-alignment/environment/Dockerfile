FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /root

RUN python -m pip install --upgrade pip && \
    python -m pip install numpy==1.26.4 pytest==8.4.1

COPY input.mp4 /root/input.mp4
COPY atrium_annotations.json /root/atrium_annotations.json
COPY skills /root/.codex/skills
