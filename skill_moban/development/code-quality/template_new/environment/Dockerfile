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

COPY settlement-gateway /services/settlement-gateway
COPY workspace /app/workspace

RUN pip install \
    fastapi==0.115.5 \
    pytest==8.3.3 \
    pytest-json-ctrf==0.3.7 \
    requests==2.32.3 \
    uvicorn==0.32.1

COPY skills/settlement-quality-audit /logs/agent/skills/settlement-quality-audit

RUN mkdir -p /app/workspace/out /app/workspace/state /logs/verifier \
    && chown -R appuser:appuser /app /home/appuser /logs \
    && chown root:svcuser /services \
    && chown -R svcuser:svcuser /services/settlement-gateway \
    && chmod 750 /services /services/settlement-gateway /services/settlement-gateway/data \
    && find /services/settlement-gateway -type f -exec chmod 640 {} + \
    && chmod -R a+rX /app/workspace

ENV HOME=/home/appuser
ENV WORKSPACE_ROOT=/app/workspace
ENV SETTLEMENT_GATEWAY_URL=http://127.0.0.1:8320
ENV SETTLEMENT_GATEWAY_TOKEN=settlement-gateway-demo-token

RUN printf '#!/bin/bash\n\
set -euo pipefail\n\
\n\
if ! curl -fsS http://127.0.0.1:8320/health >/dev/null 2>&1; then\n\
  env HOME=/home/svcuser SETTLEMENT_GATEWAY_TOKEN=\"$SETTLEMENT_GATEWAY_TOKEN\" runuser -u svcuser --preserve-environment -- python /services/settlement-gateway/server.py >/tmp/settlement-gateway.log 2>&1 &\n\
  for i in $(seq 1 60); do\n\
    if curl -fsS http://127.0.0.1:8320/health >/dev/null 2>&1; then\n\
      break\n\
    fi\n\
    sleep 0.5\n\
  done\n\
fi\n\
\n\
curl -fsS http://127.0.0.1:8320/health >/dev/null 2>&1 || {\n\
  echo \"settlement-gateway failed to start\" >&2\n\
  exit 1\n\
}\n\
\n\
exec env HOME=/home/appuser SETTLEMENT_GATEWAY_TOKEN=\"$SETTLEMENT_GATEWAY_TOKEN\" runuser -u appuser --preserve-environment -- \"$@\"\n' > /usr/local/bin/code-quality-entrypoint \
    && chmod 755 /usr/local/bin/code-quality-entrypoint

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/code-quality-entrypoint"]
CMD ["/bin/bash"]
