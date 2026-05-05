FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV HOME=/root
ENV TASK_ROOT=/app
ENV TASK_BUNDLE_ROOT=/app/knowledge-base
ENV TASK_WORKSPACE_ROOT=/app/workspace
ENV TASK_OUTPUT_ROOT=/app/output

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        nodejs \
        npm \
        ripgrep \
        tini \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir pytest
RUN npm install -g @openai/codex@0.128.0

COPY . /opt/knowledge-base-task-env

RUN mkdir -p /app/knowledge-base /app/workspace /app/output /app/skills /environment/knowledge-base /environment/workspace /environment/skills /root/.codex/skills /root/.claude/skills /etc/claude-code/.claude/skills /logs/agent/skills /logs/verifier /opt/task-baselines \
    && cp -R /opt/knowledge-base-task-env/knowledge_base/. /app/knowledge-base/ \
    && cp -R /opt/knowledge-base-task-env/workspace/. /app/workspace/ \
    && cp -R /opt/knowledge-base-task-env/knowledge_base/. /environment/knowledge-base/ \
    && cp -R /opt/knowledge-base-task-env/workspace/. /environment/workspace/ \
    && if [ -d /opt/knowledge-base-task-env/skills ]; then cp -R /opt/knowledge-base-task-env/skills/. /app/skills/; fi \
    && if [ -d /opt/knowledge-base-task-env/skills ]; then cp -R /opt/knowledge-base-task-env/skills/. /environment/skills/; fi \
    && if [ -d /opt/knowledge-base-task-env/skills ]; then cp -R /opt/knowledge-base-task-env/skills/. /root/.codex/skills/; fi \
    && if [ -d /opt/knowledge-base-task-env/skills ]; then cp -R /opt/knowledge-base-task-env/skills/. /root/.claude/skills/; fi \
    && if [ -d /opt/knowledge-base-task-env/skills ]; then cp -R /opt/knowledge-base-task-env/skills/. /etc/claude-code/.claude/skills/; fi \
    && if [ -d /opt/knowledge-base-task-env/skills ]; then cp -R /opt/knowledge-base-task-env/skills/. /logs/agent/skills/; fi \
    && cd /app/knowledge-base && find . -type f -print0 | sort -z | xargs -0 sha256sum > /opt/task-baselines/knowledge-base.sha256 \
    && if [ -d /root/.codex/skills/resource-curator ]; then cd /root/.codex/skills/resource-curator && find . -type f -print0 | sort -z | xargs -0 sha256sum > /opt/task-baselines/resource-curator.sha256; else printf '' > /opt/task-baselines/resource-curator.sha256; fi \
    && chmod -R a+rwX /app/workspace /app/output /logs \
    && chmod 755 /app/workspace/curate_resources.py \
    && chmod 644 /opt/task-baselines/knowledge-base.sha256 /opt/task-baselines/resource-curator.sha256

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/bin/bash"]
