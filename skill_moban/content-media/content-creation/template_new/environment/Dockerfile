FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV HOME=/root
ENV TASK_ROOT=/app
ENV TASK_INPUT_ROOT=/app/input
ENV TASK_WORKSPACE_ROOT=/app/workspace
ENV TASK_OUTPUT_ROOT=/app/output

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        coreutils \
        findutils \
        grep \
        jq \
        procps \
        ripgrep \
        sed \
        tini \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    pytest \
    pytest-json-ctrf

COPY input /app/input
COPY workspace /app/workspace
COPY skills /root/.codex/skills

RUN mkdir -p /app/output /logs/verifier /opt/task-baselines /root/.codex/skills \
    && if [ -d /app/input ]; then cd /app/input && find . -type f -print0 | sort -z | xargs -0 sha256sum > /opt/task-baselines/input.sha256; else printf '' > /opt/task-baselines/input.sha256; fi \
    && chmod -R a+rwX /app/workspace /app/output /logs /root/.codex \
    && if [ -f /app/workspace/build_content_pack.py ]; then chmod 755 /app/workspace/build_content_pack.py; fi \
    && chmod 644 /opt/task-baselines/input.sha256

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/bin/bash"]
