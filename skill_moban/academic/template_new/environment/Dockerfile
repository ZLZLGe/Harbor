FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV NPM_CONFIG_REGISTRY=https://registry.npmjs.org/

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    golang-go \
    nodejs \
    npm \
    tini \
    && rm -rf /var/lib/apt/lists/*

RUN /usr/bin/npm install -g @openai/codex@0.120.0

RUN printf '#!/bin/bash\n\
set -e\n\
REAL_NPM=/usr/bin/npm\n\
if [ "$#" -ge 3 ] && [ "$1" = "install" ] && [ "$2" = "-g" ] && [[ "$3" == @openai/codex@* ]]; then\n\
  if command -v codex >/dev/null 2>&1; then\n\
    echo "Using preinstalled $(codex --version)"\n\
    exit 0\n\
  fi\n\
fi\n\
exec "$REAL_NPM" "$@"\n' > /usr/local/bin/npm && chmod +x /usr/local/bin/npm

RUN pip install \
    backports.tarfile==1.2.0 \
    requests==2.32.3 \
    bibtexparser==1.4.2 \
    pytest==8.3.3

RUN useradd -m -s /bin/bash appuser

WORKDIR /opt/academic-api-hidden

COPY academic-api/hidden_service.go /tmp/hidden_service.go

RUN mkdir -p /services/academic-api \
    && CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -trimpath -ldflags="-s -w" -o /opt/academic-api-hidden/academic-api-server /tmp/hidden_service.go \
    && rm -f /tmp/hidden_service.go \
    && apt-get purge -y golang-go \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/* \
    && printf '#!/bin/bash\n\
exec /opt/academic-api-hidden/academic-api-server "$@"\n' > /services/academic-api/server \
    && printf '#!/usr/bin/env python3\n\
import os\n\
import sys\n\
\n\
if __name__ == "__main__":\n\
    os.execv("/opt/academic-api-hidden/academic-api-server", ["academic-api-server", *sys.argv[1:]])\n' > /services/academic-api/server.py \
    && chown -R appuser:appuser /opt/academic-api-hidden /services/academic-api \
    && chmod 700 /opt/academic-api-hidden \
    && chmod 700 /opt/academic-api-hidden/academic-api-server \
    && chmod 755 /services/academic-api \
    && chmod 755 /services/academic-api/server /services/academic-api/server.py

WORKDIR /app

COPY workspace/ /app/workspace/

# Keep a single Codex-visible copy of the task skill to avoid duplicate
# registration in the runtime system prompt.
COPY skills/systematic-literature-review /app/.codex/skills/systematic-literature-review
COPY skills/systematic-literature-review/scripts/apply_repairs.py /app/apply_review_repairs.py
COPY skills/systematic-literature-review/QUICKSTART.md /app/SKILL_QUICKSTART.md

RUN mkdir -p /app/output /logs/verifier \
    && chown -R appuser:appuser /app /home/appuser /logs/verifier

ENV ACADEMIC_API_URL=http://127.0.0.1:8123
ENV HIDDEN_SERVICE_ROOT=/opt/academic-api-hidden
ENV HOME=/home/appuser

RUN printf '#!/bin/bash\n\
set -euo pipefail\n\
\n\
if ! curl -fsS http://127.0.0.1:8123/health >/dev/null 2>&1; then\n\
  if [ -x /opt/academic-api-hidden/academic-api-server ]; then\n\
    /opt/academic-api-hidden/academic-api-server >/tmp/academic-api.log 2>&1 &\n\
    for i in $(seq 1 60); do\n\
      if curl -fsS http://127.0.0.1:8123/health >/dev/null 2>&1; then\n\
        break\n\
      fi\n\
      sleep 0.5\n\
    done\n\
  fi\n\
fi\n\
\n\
curl -fsS http://127.0.0.1:8123/health >/dev/null 2>&1 || {\n\
  echo \"Hidden academic API failed to start\" >&2\n\
  exit 1\n\
}\n\
\n\
exec \"$@\"\n' > /usr/local/bin/academic-entrypoint \
    && chmod 755 /usr/local/bin/academic-entrypoint

USER appuser

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/academic-entrypoint"]
CMD ["/bin/bash"]
