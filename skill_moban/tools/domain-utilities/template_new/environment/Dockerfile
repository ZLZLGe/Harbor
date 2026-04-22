FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV HOME=/home/appuser

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gosu \
    tini \
    ripgrep \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash appuser

WORKDIR /app

COPY data /app/data
COPY hidden-service-src /services/domain-audit
COPY skills /app/.codex/skills
COPY skills /home/appuser/.codex/skills
COPY build-scripts/write_protected_hashes.py /opt/domain-task/write_protected_hashes.py

RUN pip install \
    pytest==8.3.3 \
    pytest-json-ctrf==0.3.7 \
    requests==2.32.3

RUN mkdir -p /app/output /logs/verifier /opt/domain-task \
    && python3 /opt/domain-task/write_protected_hashes.py

RUN chown -R appuser:appuser /app /home/appuser /logs/verifier \
    && chown -R root:root /services/domain-audit /opt/domain-task \
    && chmod -R 755 /services/domain-audit \
    && chmod -R 755 /opt/domain-task

RUN printf '#!/bin/bash\n\
set -euo pipefail\n\
\n\
mkdir -p \"$HOME/.codex/skills\" /app/.codex/skills\n\
if ! curl -fsS http://127.0.0.1:8331/health >/dev/null 2>&1; then\n\
  nohup python3 /services/domain-audit/server.py >/tmp/domain-audit.log 2>&1 &\n\
  for i in $(seq 1 60); do\n\
    if curl -fsS http://127.0.0.1:8331/health >/dev/null 2>&1; then\n\
      break\n\
    fi\n\
    sleep 0.5\n\
  done\n\
fi\n\
\n\
curl -fsS http://127.0.0.1:8331/health >/dev/null 2>&1 || {\n\
  echo \"domain-audit failed to start\" >&2\n\
  [ -f /tmp/domain-audit.log ] && cat /tmp/domain-audit.log >&2 || true\n\
  exit 1\n\
}\n\
\n\
exec gosu appuser \"$@\"\n' > /usr/local/bin/domain-utilities-entrypoint \
    && chmod 755 /usr/local/bin/domain-utilities-entrypoint

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/domain-utilities-entrypoint"]
CMD ["/bin/bash"]
