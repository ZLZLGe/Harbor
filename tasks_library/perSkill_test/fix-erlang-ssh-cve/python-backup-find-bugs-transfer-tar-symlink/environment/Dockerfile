FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends git bash ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY workspace /app/workspace

WORKDIR /app/workspace

COPY skills /root/.codex/skills
