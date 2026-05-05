FROM python:3.12-slim

WORKDIR /root

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends tini ripgrep \
    && rm -rf /var/lib/apt/lists/*

COPY vendor/runtime/python-site.tar.gz /tmp/python-site.tar.gz

RUN mkdir -p /tmp/task-python /usr/local/lib/python3.12/site-packages \
    && tar -xzf /tmp/python-site.tar.gz -C /tmp/task-python --strip-components=1 \
    && cp -a /tmp/task-python/. /usr/local/lib/python3.12/site-packages/ \
    && if [ -d /tmp/task-python/bin ]; then cp -a /tmp/task-python/bin/. /usr/local/bin/; fi \
    && rm -rf /tmp/task-python /tmp/python-site.tar.gz

COPY . /root/environment

RUN mkdir -p /root/.codex \
    && if [ -d /root/environment/skills ]; then cp -a /root/environment/skills /root/.codex/skills; fi \
    && mkdir -p /services \
    && cp -a /root/environment/services/promo-enrichment /services/promo-enrichment \
    && chmod +x /root/environment/pipeline/run_analysis.py /services/promo-enrichment/server.py
