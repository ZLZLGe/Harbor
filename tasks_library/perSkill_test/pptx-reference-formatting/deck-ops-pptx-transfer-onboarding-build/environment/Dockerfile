FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    libcairo2 \
    libffi-dev \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages \
    cairosvg==2.7.1 \
    lxml==5.3.0 \
    pillow==11.1.0 \
    pytest==8.4.1 \
    python-pptx==1.0.2

WORKDIR /root

COPY brief.md /root/brief.md
COPY metrics.json /root/metrics.json
COPY brand /root/brand

COPY skills /root/.codex/skills
