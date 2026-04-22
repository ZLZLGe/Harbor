FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    make \
    tini \
    util-linux \
    && rm -rf /var/lib/apt/lists/*

RUN pip install \
    duckdb==1.2.2 \
    fastapi==0.115.5 \
    pandas==2.2.3 \
    pytest==8.3.3 \
    pytest-json-ctrf==0.3.7 \
    requests==2.32.3 \
    uvicorn==0.32.1

RUN useradd -m -s /bin/bash appuser \
    && useradd -m -s /bin/bash svcuser

WORKDIR /app

COPY audit-service/server.pyc /services/audit-service/server.pyc
COPY audit-service/server.bin /services/audit-service/server.bin
COPY workspace /app/workspace
COPY skills /opt/task-skills
COPY skills /root/.codex/skills

RUN mkdir -p /app/output /logs/verifier /opt/task-skills /services/audit-service \
    && sha256sum /services/audit-service/server.bin | awk '{print $1}' > /opt/audit-service.sha256

RUN chown -R appuser:appuser /app /home/appuser /logs /opt/task-skills \
    && chown root:svcuser /services \
    && chown -R svcuser:svcuser /services/audit-service \
    && chmod 750 /services /services/audit-service \
    && chmod 644 /services/audit-service/server.pyc \
    && chmod 755 /services/audit-service/server.bin \
    && chmod -R a+rX /app/workspace /root/.codex/skills

ENV HOME=/home/appuser
ENV PYTHONPATH=/app/workspace
ENV PUBLISH_AUDIT_URL=http://127.0.0.1:8331

RUN printf '#!/bin/bash\n\
set -euo pipefail\n\
\n\
mkdir -p \"$HOME/.codex/skills\" /app/.codex/skills\n\
if [ -d /opt/task-skills ]; then\n\
  for skill in /opt/task-skills/*; do\n\
    [ -d \"$skill\" ] || continue\n\
    name=\"$(basename \"$skill\")\"\n\
    mkdir -p \"$HOME/.codex/skills/$name\" \"/app/.codex/skills/$name\"\n\
    cp -R \"$skill/.\" \"$HOME/.codex/skills/$name/\"\n\
    cp -R \"$skill/.\" \"/app/.codex/skills/$name/\"\n\
  done\n\
fi\n\
\n\
if [ -f /opt/task-skills/cdc-lakehouse-publish/probe_marketplace_snapshot.py ]; then\n\
  chmod 755 /root/.codex/skills/cdc-lakehouse-publish/*.py\n\
  ln -sf /root/.codex/skills/cdc-lakehouse-publish/probe_marketplace_snapshot.py /usr/local/bin/probe_marketplace_snapshot\n\
  ln -sf /root/.codex/skills/cdc-lakehouse-publish/submit_marketplace_bundle.py /usr/local/bin/submit_marketplace_bundle\n\
  ln -sf /root/.codex/skills/cdc-lakehouse-publish/build_and_publish_marketplace_snapshot.py /usr/local/bin/build_and_publish_marketplace_snapshot\n\
  cp /opt/task-skills/cdc-lakehouse-publish/SKILL.md /app/TASK_SKILL.md\n\
  cp /opt/task-skills/cdc-lakehouse-publish/SKILL.md /app/000_TASK_SKILL_README.md\n\
  cp /opt/task-skills/cdc-lakehouse-publish/START_HERE.md /app/000_START_HERE_WITH_SKILL.md\n\
  cp /opt/task-skills/cdc-lakehouse-publish/START_HERE.md /app/README.md\n\
  cp /opt/task-skills/cdc-lakehouse-publish/probe_marketplace_snapshot.py /app/skill_probe_marketplace_snapshot.py\n\
  cp /opt/task-skills/cdc-lakehouse-publish/probe_marketplace_snapshot.py /app/001_skill_probe_marketplace_snapshot.py\n\
  cp /opt/task-skills/cdc-lakehouse-publish/submit_marketplace_bundle.py /app/skill_submit_marketplace_bundle.py\n\
  cp /opt/task-skills/cdc-lakehouse-publish/submit_marketplace_bundle.py /app/002_skill_submit_marketplace_bundle.py\n\
  cp /opt/task-skills/cdc-lakehouse-publish/build_and_publish_marketplace_snapshot.py /app/skill_build_and_publish_marketplace_snapshot.py\n\
  cp /opt/task-skills/cdc-lakehouse-publish/build_and_publish_marketplace_snapshot.py /app/003_skill_build_and_publish_marketplace_snapshot.py\n\
  cp /opt/task-skills/cdc-lakehouse-publish/validate_marketplace_snapshot.py /app/skill_validate_marketplace_snapshot.py\n\
  cp /opt/task-skills/cdc-lakehouse-publish/validate_marketplace_snapshot.py /app/004_skill_validate_marketplace_snapshot.py\n\
  chmod 644 /app/TASK_SKILL.md /app/000_TASK_SKILL_README.md /app/000_START_HERE_WITH_SKILL.md /app/README.md\n\
  chmod 755 /app/skill_probe_marketplace_snapshot.py /app/001_skill_probe_marketplace_snapshot.py /app/skill_submit_marketplace_bundle.py /app/002_skill_submit_marketplace_bundle.py /app/skill_build_and_publish_marketplace_snapshot.py /app/003_skill_build_and_publish_marketplace_snapshot.py /app/skill_validate_marketplace_snapshot.py /app/004_skill_validate_marketplace_snapshot.py\n\
fi\n\
\n\
if ! curl -fsS http://127.0.0.1:8331/health >/dev/null 2>&1; then\n\
  env HOME=/home/svcuser runuser -u svcuser --preserve-environment -- python3 /services/audit-service/server.pyc >/tmp/marketplace-audit.log 2>&1 &\n\
  for i in $(seq 1 60); do\n\
    if curl -fsS http://127.0.0.1:8331/health >/dev/null 2>&1; then\n\
      break\n\
    fi\n\
    sleep 0.5\n\
  done\n\
fi\n\
\n\
curl -fsS http://127.0.0.1:8331/health >/dev/null 2>&1 || {\n\
  echo \"publish audit service failed to start\" >&2\n\
  [ -f /tmp/marketplace-audit.log ] && cat /tmp/marketplace-audit.log >&2 || true\n\
  exit 1\n\
}\n\
\n\
exec env HOME=/home/appuser PYTHONPATH=/app/workspace runuser -u appuser --preserve-environment -- \"$@\"\n' > /usr/local/bin/data-engineering-entrypoint \
    && chmod 755 /usr/local/bin/data-engineering-entrypoint

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/data-engineering-entrypoint"]
CMD ["/bin/bash"]
