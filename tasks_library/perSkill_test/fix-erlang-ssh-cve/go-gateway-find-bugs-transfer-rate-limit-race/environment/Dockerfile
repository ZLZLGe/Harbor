FROM golang:1.22-bookworm

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        git \
        python3 \
    && rm -rf /var/lib/apt/lists/*

COPY workspace /app/workspace

WORKDIR /app/workspace

COPY skills /root/.codex/skills
