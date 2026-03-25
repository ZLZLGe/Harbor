FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    curl \
    nodejs \
    npm \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN npm install --prefix /opt/d3 d3@7.9.0 --silent

RUN pip3 install --break-system-packages pytest playwright && \
    playwright install --with-deps chromium

WORKDIR /root

COPY data /root/data
COPY skills /root/.codex/skills
