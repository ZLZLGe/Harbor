FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /root

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    nodejs \
    npm \
    python3 \
    python3-pip \
    python3-pytest \
    python-is-python3 \
    tini \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /root/environment/data /root/environment/workspace /root/.codex/skills /root/answer

COPY . /root/environment
COPY skills /root/.codex/skills
