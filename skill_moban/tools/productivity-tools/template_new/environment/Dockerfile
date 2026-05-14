FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV HOME=/root
ENV BASH_ENV=/etc/codex-command-hint.sh
ENV TASK_ROOT=/app
ENV TASK_BUNDLE_ROOT=/app/release-watch
ENV TASK_WORKSPACE_ROOT=/app/workspace
ENV TASK_OUTPUT_ROOT=/app/output
ENV BLOGWATCHER_VERSION=0.0.3

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        curl \
        ripgrep \
        tini \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir pytest

COPY . /opt/productivity-tools-task-env

RUN curl -fsSL -o /tmp/blogwatcher.tar.gz \
        https://github.com/Hyaxia/blogwatcher/releases/download/v0.0.3/blogwatcher_0.0.3_linux_amd64.tar.gz \
    && tar -xzf /tmp/blogwatcher.tar.gz -C /usr/local/bin blogwatcher \
    && chmod 755 /usr/local/bin/blogwatcher \
    && rm -f /tmp/blogwatcher.tar.gz

RUN python3 /opt/productivity-tools-task-env/setup_environment.py

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/bin/bash"]
