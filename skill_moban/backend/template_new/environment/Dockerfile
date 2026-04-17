FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    nodejs \
    npm \
    tini \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash appuser

WORKDIR /app

COPY inventory-ledger /services/inventory-ledger
COPY workspace /app/workspace
COPY workspace/checkout-api/requirements.txt /tmp/checkout-api-requirements.txt

RUN pip install -r /tmp/checkout-api-requirements.txt \
    && pip install pytest==8.3.3 pytest-json-ctrf==0.3.7 \
    && rm -f /tmp/checkout-api-requirements.txt

COPY skills/inventory-hold-debugging /logs/agent/skills/inventory-hold-debugging

RUN mkdir -p /app/output /logs/verifier /app/workspace/state \
    && chown -R appuser:appuser /app /home/appuser /logs /services/inventory-ledger

ENV HOME=/home/appuser
ENV PYTHONPATH=/app/workspace/checkout-api
ENV CHECKOUT_DB_PATH=/app/workspace/state/checkout.db
ENV LEDGER_API_URL=http://127.0.0.1:8131
ENV CHECKOUT_API_URL=http://127.0.0.1:8120
ENV INVENTORY_LEDGER_SEED=/app/workspace/data/catalog/ledger_seed.json

RUN printf '#!/bin/bash\n\
set -euo pipefail\n\
\n\
if ! curl -fsS http://127.0.0.1:8131/health >/dev/null 2>&1; then\n\
  python /services/inventory-ledger/server.py >/tmp/inventory-ledger.log 2>&1 &\n\
  for i in $(seq 1 60); do\n\
    if curl -fsS http://127.0.0.1:8131/health >/dev/null 2>&1; then\n\
      break\n\
    fi\n\
    sleep 0.5\n\
  done\n\
fi\n\
\n\
curl -fsS http://127.0.0.1:8131/health >/dev/null 2>&1 || {\n\
  echo \"inventory-ledger failed to start\" >&2\n\
  exit 1\n\
}\n\
\n\
exec \"$@\"\n' > /usr/local/bin/backend-entrypoint \
    && chmod 755 /usr/local/bin/backend-entrypoint

USER appuser

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/backend-entrypoint"]
CMD ["/bin/bash"]
