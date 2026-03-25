FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pytest \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

COPY Webinar-Rehearsal.pptx /root/
COPY speaker_notes.json /root/
COPY skills /root/.codex/skills
