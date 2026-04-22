FROM python:3.12-slim

WORKDIR /root

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends ripgrep tini \
    && rm -rf /var/lib/apt/lists/*

COPY vendor/runtime/python-site.tar.gz /tmp/python-site.tar.gz

RUN mkdir -p /tmp/task-python /usr/local/lib/python3.12/site-packages \
    && tar -xzf /tmp/python-site.tar.gz -C /tmp/task-python --strip-components=1 \
    && cp -a /tmp/task-python/. /usr/local/lib/python3.12/site-packages/ \
    && if [ -d /tmp/task-python/bin ]; then cp -a /tmp/task-python/bin/. /usr/local/bin/; fi \
    && rm -rf /tmp/task-python /tmp/python-site.tar.gz

COPY skills /root/.codex/skills
COPY data /root/environment/data
COPY broken_outputs /root/environment/broken_outputs
COPY pipeline /root/environment/pipeline
COPY services/panel-annotation /services/panel-annotation

RUN chmod +x \
    /root/environment/pipeline/run_analysis.py \
    /services/panel-annotation/server.py
