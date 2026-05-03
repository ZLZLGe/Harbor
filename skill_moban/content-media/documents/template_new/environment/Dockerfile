FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV HOME=/root
ENV TASK_ROOT=/app
ENV TASK_BRIEFING_ROOT=/app/briefing
ENV TASK_WORKSPACE_ROOT=/app/workspace
ENV TASK_OUTPUT_ROOT=/app/output

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        coreutils \
        curl \
        findutils \
        git \
        grep \
        libreoffice-core \
        libreoffice-writer \
        nodejs \
        npm \
        pandoc \
        procps \
        ripgrep \
        sed \
        tini \
        unzip \
        zip \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    defusedxml \
    matplotlib \
    pandas \
    pillow \
    python-docx \
    pytest \
    pytest-json-ctrf \
    requests

RUN npm install -g @openai/codex@0.120.0

COPY . /opt/documents-task-env

RUN mkdir -p /app/briefing /app/workspace /app/output /root/.codex/skills /root/.claude/skills /etc/claude-code/.claude/skills /logs/agent/skills /logs/verifier /opt/task-baselines \
    && cp -R /opt/documents-task-env/briefing/. /app/briefing/ \
    && cp -R /opt/documents-task-env/workspace/. /app/workspace/ \
    && if [ -d /opt/documents-task-env/skills ]; then cp -R /opt/documents-task-env/skills/. /root/.codex/skills/; fi \
    && if [ -d /opt/documents-task-env/skills ]; then cp -R /opt/documents-task-env/skills/. /root/.claude/skills/; fi \
    && if [ -d /opt/documents-task-env/skills ]; then cp -R /opt/documents-task-env/skills/. /etc/claude-code/.claude/skills/; fi \
    && if [ -d /opt/documents-task-env/skills ]; then cp -R /opt/documents-task-env/skills/. /logs/agent/skills/; fi \
    && find /app/briefing -type f -print0 | sort -z | xargs -0 sha256sum > /opt/task-baselines/briefing.sha256 \
    && if [ -d /root/.codex/skills/docx ]; then cd /root/.codex/skills/docx && find . -type f -print0 | sort -z | xargs -0 sha256sum > /opt/task-baselines/docx-skill.sha256; else printf '' > /opt/task-baselines/docx-skill.sha256; fi \
    && chmod -R a+rwX /app/workspace /app/output /logs \
    && chmod 755 /app/workspace/build_packet.py \
    && chmod 644 /opt/task-baselines/briefing.sha256 /opt/task-baselines/docx-skill.sha256

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/bin/bash"]
