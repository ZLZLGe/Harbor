FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    coreutils \
    curl \
    jq \
    nodejs \
    npm \
    ripgrep \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --no-cache-dir pandas==2.2.3 PyYAML==6.0.2

RUN mkdir -p /root/data /root/output /root/.codex/skills /logs/agent/skills /logs/verifier

COPY . /tmp/noticeflow-environment
COPY skills /tmp/noticeflow-environment/skills
COPY skills /root/.codex/skills
COPY skills /logs/agent/skills

RUN cp -R /tmp/noticeflow-environment/data/. /root/data/ \
    && rm -rf /tmp/noticeflow-environment \
    && find /root/data -type f -print0 | sort -z | xargs -0 sha256sum > /opt/noticeflow-data.sha256 \
    && chmod 644 /opt/noticeflow-data.sha256 \
    && chmod -R a+r /root/data /root/.codex/skills /logs/agent/skills \
    && chmod 777 /root/output /logs/verifier

CMD ["/bin/bash"]
