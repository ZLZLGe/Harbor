FROM python:3.12-slim

WORKDIR /root

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends ripgrep tini curl \
    && rm -rf /var/lib/apt/lists/*

COPY vendor/python-site.tar.gz /tmp/python-site.tar.gz

RUN mkdir -p /tmp/task-python /usr/local/lib/python3.12/site-packages \
    && tar -xzf /tmp/python-site.tar.gz -C /tmp/task-python \
    && cp -a /tmp/task-python/. /usr/local/lib/python3.12/site-packages/ \
    && rm -rf /tmp/task-python /tmp/python-site.tar.gz

COPY skills /root/.codex/skills
COPY data /root/environment/data
COPY pipeline /root/environment/pipeline
COPY services/field-context /services/field-context

RUN chmod +x \
    /root/environment/pipeline/run_transient_triage.py \
    /services/field-context/server.py
