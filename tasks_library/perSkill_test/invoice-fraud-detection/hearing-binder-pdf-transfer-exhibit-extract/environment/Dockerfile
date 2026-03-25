FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

COPY bundle_manifest.json /root/bundle_manifest.json
COPY create_hearing_assets.py /tmp/create_hearing_assets.py
COPY skills /root/.codex/skills

RUN pip3 install --break-system-packages \
    pypdf==5.4.0 \
    reportlab==4.2.5 \
    pytest==8.4.1

RUN python3 /tmp/create_hearing_assets.py
