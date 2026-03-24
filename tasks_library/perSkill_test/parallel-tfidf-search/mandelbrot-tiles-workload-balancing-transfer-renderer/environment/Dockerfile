FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

RUN mkdir -p /root/workspace
COPY workspace/ /root/workspace/
COPY skills /root/.codex/skills

CMD ["python", "--version"]
