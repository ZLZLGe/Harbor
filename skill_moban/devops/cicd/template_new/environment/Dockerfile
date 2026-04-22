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

RUN useradd -m -s /bin/bash appuser \
    && useradd -m -s /bin/bash svcuser

WORKDIR /app

COPY release-broker /services/release-broker
COPY workspace /app/workspace

RUN pip install \
    fastapi==0.115.5 \
    pyyaml==6.0.2 \
    requests==2.32.3 \
    uvicorn==0.32.1 \
    pytest==8.3.3 \
    pytest-json-ctrf==0.3.7

COPY skills/github-actions-release-audit /opt/task-skills/github-actions-release-audit

RUN mkdir -p /app/workspace/out /app/workspace/state /logs/verifier /opt/task-skills \
    && chown -R appuser:appuser /app /home/appuser /logs \
    && chown root:svcuser /services \
    && chown -R svcuser:svcuser /services/release-broker \
    && chmod 750 /services /services/release-broker /services/release-broker/data \
    && find /services/release-broker -type f -exec chmod 640 {} + \
    && chmod -R a+rX /app/workspace /opt/task-skills

ENV HOME=/home/appuser
ENV WORKSPACE_ROOT=/app/workspace
ENV RELEASE_BROKER_URL=http://127.0.0.1:8310
ENV RELEASE_BROKER_TOKEN=release-broker-demo-token

RUN printf '#!/bin/bash\n\
set -euo pipefail\n\
\n\
if ! curl -fsS http://127.0.0.1:8310/health >/dev/null 2>&1; then\n\
  env HOME=/home/svcuser RELEASE_BROKER_TOKEN=\"$RELEASE_BROKER_TOKEN\" runuser -u svcuser --preserve-environment -- python /services/release-broker/server.py >/tmp/release-broker.log 2>&1 &\n\
  for i in $(seq 1 60); do\n\
    if curl -fsS http://127.0.0.1:8310/health >/dev/null 2>&1; then\n\
      break\n\
    fi\n\
    sleep 0.5\n\
  done\n\
fi\n\
\n\
curl -fsS http://127.0.0.1:8310/health >/dev/null 2>&1 || {\n\
  echo \"release-broker failed to start\" >&2\n\
  exit 1\n\
}\n\
\n\
exec env HOME=/home/appuser RELEASE_BROKER_TOKEN=\"$RELEASE_BROKER_TOKEN\" runuser -u appuser --preserve-environment -- \"$@\"\n' > /usr/local/bin/cicd-entrypoint \
    && chmod 755 /usr/local/bin/cicd-entrypoint

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/cicd-entrypoint"]
CMD ["/bin/bash"]
