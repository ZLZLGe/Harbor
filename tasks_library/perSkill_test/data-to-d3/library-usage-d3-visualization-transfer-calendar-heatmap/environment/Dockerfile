FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    nodejs \
    npm \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages pytest

RUN mkdir -p /root/task-deps && \
    cd /root/task-deps && \
    npm init -y >/dev/null 2>&1 && \
    npm install d3@7.9.0 --silent && \
    ln -sfn /root/task-deps/node_modules /root/node_modules

WORKDIR /root

COPY data /root/data
COPY skills /root/.codex/skills
