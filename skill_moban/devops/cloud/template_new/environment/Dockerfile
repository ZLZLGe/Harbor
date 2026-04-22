FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    tini \
    util-linux \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash appuser \
    && useradd -m -s /bin/bash svcuser

WORKDIR /app

COPY control-plane /services/control-plane
COPY mirror-service /services/mirror-service
COPY workspace /app/workspace
COPY workspace/rollout-api/requirements.txt /tmp/rollout-api-requirements.txt

RUN pip install -r /tmp/rollout-api-requirements.txt \
    && pip install pytest==8.3.3 pytest-json-ctrf==0.3.7 \
    && rm -f /tmp/rollout-api-requirements.txt

COPY skills/azure-deployment-preflight /logs/agent/skills/azure-deployment-preflight

RUN mkdir -p /app/output /logs/verifier /app/workspace/state \
    && chown -R appuser:appuser /app /home/appuser /logs \
    && chown root:svcuser /services \
    && chown -R svcuser:svcuser /services/control-plane /services/mirror-service \
    && chmod 750 /services /services/control-plane /services/mirror-service /services/mirror-service/data \
    && find /services/control-plane -type f -exec chmod 640 {} + \
    && find /services/mirror-service -type f -exec chmod 640 {} + \
    && chmod -R a+rX /app/workspace

ENV HOME=/home/appuser
ENV WORKSPACE_ROOT=/app/workspace
ENV CONTROL_PLANE_URL=http://127.0.0.1:8300
ENV PUBLIC_API_URL=http://127.0.0.1:8300
ENV MIRROR_API_URL=http://127.0.0.1:8320
ENV DEPLOYMENT_TEMPLATE_PATH=/app/workspace/infra/containerapp.template.json

RUN printf '#!/bin/bash\n\
set -euo pipefail\n\
\n\
if ! curl -fsS http://127.0.0.1:8320/health >/dev/null 2>&1; then\n\
  env HOME=/home/svcuser runuser -u svcuser --preserve-environment -- python /services/mirror-service/server.py >/tmp/mirror-service.log 2>&1 &\n\
  for i in $(seq 1 60); do\n\
    if curl -fsS http://127.0.0.1:8320/health >/dev/null 2>&1; then\n\
      break\n\
    fi\n\
    sleep 0.5\n\
  done\n\
fi\n\
\n\
if ! curl -fsS http://127.0.0.1:8300/__control/status >/dev/null 2>&1; then\n\
  env HOME=/home/svcuser runuser -u svcuser --preserve-environment -- python /services/control-plane/server.py >/tmp/control-plane.log 2>&1 &\n\
  for i in $(seq 1 60); do\n\
    if curl -fsS http://127.0.0.1:8300/__control/status >/dev/null 2>&1; then\n\
      break\n\
    fi\n\
    sleep 0.5\n\
  done\n\
fi\n\
\n\
curl -fsS http://127.0.0.1:8320/health >/dev/null 2>&1 || {\n\
  echo \"mirror-service failed to start\" >&2\n\
  exit 1\n\
}\n\
\n\
curl -fsS http://127.0.0.1:8300/__control/status >/dev/null 2>&1 || {\n\
  echo \"control-plane failed to start\" >&2\n\
  exit 1\n\
}\n\
\n\
exec env HOME=/home/appuser runuser -u appuser --preserve-environment -- \"$@\"\n' > /usr/local/bin/cloud-entrypoint \
    && chmod 755 /usr/local/bin/cloud-entrypoint

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/cloud-entrypoint"]
CMD ["/bin/bash"]
