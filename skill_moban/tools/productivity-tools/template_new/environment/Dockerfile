FROM node:22-bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV HOME=/root
ENV PATH=/usr/local/go/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ARG GO_VERSION=1.24.5

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    jq \
    python3 \
    ripgrep \
    tar \
    tini \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL "https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz" -o /tmp/go.tgz \
    && rm -rf /usr/local/go \
    && tar -C /usr/local -xzf /tmp/go.tgz \
    && rm -f /tmp/go.tgz \
    && /usr/local/go/bin/go version

RUN node --version \
    && npm --version \
    && npm install -g @openai/codex@0.120.0 \
    && codex --version

WORKDIR /app
COPY . /tmp/template-environment

RUN mkdir -p \
      /app/bin \
      /app/data \
      /app/output \
      /app/runtime/logs \
      /app/solution \
      /app/tests \
      /app/workspace \
      /root/.codex/skills \
      /logs/agent/skills \
      /logs/verifier \
    && cp -R /tmp/template-environment/bin/. /app/bin/ \
    && cp -R /tmp/template-environment/data/. /app/data/ \
    && cp -R /tmp/template-environment/solution/. /app/solution/ \
    && cp -R /tmp/template-environment/tests/. /app/tests/ \
    && if [ -d /tmp/template-environment/skills ]; then \
         cp -R /tmp/template-environment/skills/. /root/.codex/skills/; \
         cp -R /tmp/template-environment/skills/. /logs/agent/skills/; \
       fi \
    && if [ -d /tmp/template-environment/skills/blogwatcher ]; then \
         GOBIN=/usr/local/bin /usr/local/go/bin/go install github.com/Hyaxia/blogwatcher/cmd/blogwatcher@latest; \
         blogwatcher --help >/dev/null; \
       fi \
    && find /app/data -type f -print0 | sort -z | xargs -0 sha256sum | sed 's#  /app/data/#  #' > /opt/productivity-input.sha256 \
    && if [ -f /root/.codex/skills/blogwatcher/SKILL.md ]; then \
         cd /root/.codex/skills/blogwatcher \
         && sha256sum SKILL.md > /opt/productivity-skill.sha256; \
       else \
         : > /opt/productivity-skill.sha256; \
       fi \
    && chmod +x /app/bin/start_feed_server.sh \
                /app/solution/solve.sh \
                /app/solution/create_digest.py \
    && chmod -R a+rX /app /logs/agent/skills /opt/productivity-input.sha256 /opt/productivity-skill.sha256

RUN printf '%s\n' '#!/bin/bash' \
    'set -euo pipefail' \
    '/app/bin/start_feed_server.sh >/app/runtime/logs/feed-server-start.log 2>&1 || {' \
    '  cat /app/runtime/logs/feed-server-start.log >&2' \
    '  exit 1' \
    '}' \
    'if [ "$#" -eq 0 ]; then' \
    '  exec /bin/bash' \
    'elif [ "$#" -eq 1 ]; then' \
    '  exec /bin/bash -lc "$1"' \
    'else' \
    '  exec "$@"' \
    'fi' > /usr/local/bin/feedtask-entrypoint \
    && chmod 755 /usr/local/bin/feedtask-entrypoint

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/feedtask-entrypoint"]
CMD ["/bin/bash"]
