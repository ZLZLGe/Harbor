FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV HOME=/app

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    coreutils \
    findutils \
    tini \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --no-cache-dir \
    pandas==2.2.3 \
    PyYAML==6.0.2 \
    pytest==8.3.5

WORKDIR /app

COPY data /app/data
COPY skills /opt/template-skills
COPY skills /root/.codex/skills
COPY skills /logs/agent/skills
COPY entrypoint.sh /usr/local/bin/task-entrypoint.sh

RUN mkdir -p \
      /app/output \
      /app/.codex/skills \
      /logs/agent/skills \
      /logs/verifier \
    && find /app/data -type f -print0 | sort -z | xargs -0 sha256sum > /opt/task-input.sha256 \
    && chmod +x /usr/local/bin/task-entrypoint.sh \
    && chmod -R a+rwX /app /logs

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/task-entrypoint.sh"]
CMD ["/bin/bash"]
