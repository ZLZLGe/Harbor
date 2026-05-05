FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV HOME=/root
ENV TASK_ROOT=/environment
ENV TASK_BUNDLE_ROOT=/environment/reference_bundle
ENV TASK_OUTPUT_ROOT=/environment/output
ENV TASK_SKILL_ROOT=/environment/skills/docs-changelog

WORKDIR /environment

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        nodejs \
        npm \
        tini \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir pytest
RUN npm install -g @openai/codex@0.128.0

COPY . /opt/changelog-task-env

RUN mkdir -p /environment/reference_bundle /environment/output /environment/skills /app/reference_bundle /app/output /app/skills /root/.codex/skills /root/.claude/skills /etc/claude-code/.claude/skills /logs/agent/skills /logs/verifier /opt/task-baselines \
    && cp -R /opt/changelog-task-env/reference_bundle/. /environment/reference_bundle/ \
    && cp -R /opt/changelog-task-env/reference_bundle/. /app/reference_bundle/ \
    && if [ -d /opt/changelog-task-env/skills ]; then cp -R /opt/changelog-task-env/skills/. /environment/skills/; fi \
    && if [ -d /opt/changelog-task-env/skills ]; then cp -R /opt/changelog-task-env/skills/. /app/skills/; fi \
    && if [ -d /opt/changelog-task-env/skills ]; then cp -R /opt/changelog-task-env/skills/. /root/.codex/skills/; fi \
    && if [ -d /opt/changelog-task-env/skills ]; then cp -R /opt/changelog-task-env/skills/. /root/.claude/skills/; fi \
    && if [ -d /opt/changelog-task-env/skills ]; then cp -R /opt/changelog-task-env/skills/. /etc/claude-code/.claude/skills/; fi \
    && if [ -d /opt/changelog-task-env/skills ]; then cp -R /opt/changelog-task-env/skills/. /logs/agent/skills/; fi \
    && cd /environment/reference_bundle && find . -type f -print0 | sort -z | xargs -0 sha256sum > /opt/task-baselines/reference-bundle.sha256 \
    && if [ -d /environment/skills/docs-changelog ]; then cd /environment/skills/docs-changelog && find . -type f -print0 | sort -z | xargs -0 sha256sum > /opt/task-baselines/docs-changelog.sha256; else printf '' > /opt/task-baselines/docs-changelog.sha256; fi \
    && chmod -R a+rwX /environment/output /app/output /logs \
    && chmod 755 /environment/reference_bundle/workspace/scripts/render_changelog.py \
    && chmod 644 /opt/task-baselines/reference-bundle.sha256 /opt/task-baselines/docs-changelog.sha256

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/bin/bash"]
