FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /opt/health-fitness-task-env

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    coreutils \
    curl \
    jq \
    ripgrep \
    tmux \
    && rm -rf /var/lib/apt/lists/*

COPY . /opt/health-fitness-task-env
COPY skills /root/.codex/skills
COPY skills /logs/agent/skills
COPY skills /tmp/codex-home/skills

RUN mkdir -p /root/.codex/skills /logs/agent/skills /tmp/codex-home/skills /root/data /root/output /logs/verifier \
    && cp -R /opt/health-fitness-task-env/data/. /root/data/ \
    && find /root/data -type f -print0 | sort -z | xargs -0 sha256sum > /opt/health-fitness-data.sha256 \
    && chmod 644 /opt/health-fitness-data.sha256

CMD ["/bin/bash"]
