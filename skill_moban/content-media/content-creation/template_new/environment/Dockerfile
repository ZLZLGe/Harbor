FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV CONTENT_REVIEW_PORT=8147

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    coreutils \
    curl \
    jq \
    npm \
    ripgrep \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g @openai/codex@0.120.0

COPY . /opt/content-task-environment

RUN mkdir -p /root/workspace/source_bundle /root/.codex/skills /logs/agent/skills /root/output /logs/verifier /var/log/content-review /services/content-review \
    && cp -R /opt/content-task-environment/data/. /root/workspace/source_bundle/ \
    && cp -R /opt/content-task-environment/hidden-service-src/. /services/content-review/ \
    && if [ -d /opt/content-task-environment/skills ]; then cp -R /opt/content-task-environment/skills/. /root/.codex/skills/; fi \
    && if [ -d /opt/content-task-environment/skills ]; then cp -R /opt/content-task-environment/skills/. /logs/agent/skills/; fi \
    && find /root/workspace/source_bundle -type f -print0 | sort -z | xargs -0 sha256sum > /opt/source-bundle.sha256 \
    && find /services/content-review -type f -print0 | sort -z | xargs -0 sha256sum > /opt/content-review-service.sha256 \
    && if [ -d /root/.codex/skills ]; then find /root/.codex/skills -type f -print0 | sort -z | xargs -0 sha256sum > /opt/content-skills.sha256; else printf '' > /opt/content-skills.sha256; fi \
    && chmod -R 755 /services/content-review \
    && chmod 644 /opt/source-bundle.sha256 /opt/content-review-service.sha256 /opt/content-skills.sha256 \
    && chmod 777 /var/log/content-review

RUN printf '#!/bin/bash\n\
set -euo pipefail\n\
\n\
if ! python3 -c '"'"'import urllib.request; urllib.request.urlopen(\"http://127.0.0.1:8147/health\", timeout=1).read()'"'"' >/dev/null 2>&1; then\n\
  nohup python3 /services/content-review/server.py >/tmp/content-review.log 2>&1 &\n\
  for i in $(seq 1 60); do\n\
    if python3 -c '"'"'import urllib.request; urllib.request.urlopen(\"http://127.0.0.1:8147/health\", timeout=1).read()'"'"' >/dev/null 2>&1; then\n\
      break\n\
    fi\n\
    sleep 0.5\n\
  done\n\
fi\n\
\n\
python3 -c '"'"'import urllib.request; urllib.request.urlopen(\"http://127.0.0.1:8147/health\", timeout=1).read()'"'"' >/dev/null 2>&1 || {\n\
  echo \"content review service failed to start\" >&2\n\
  [ -f /tmp/content-review.log ] && cat /tmp/content-review.log >&2 || true\n\
  exit 1\n\
}\n' > /usr/local/bin/start-content-review \
    && chmod 755 /usr/local/bin/start-content-review

RUN printf '#!/bin/bash\n\
if command -v start-content-review >/dev/null 2>&1; then\n\
  start-content-review >/tmp/content-review-profile.log 2>&1 || true\n\
fi\n' > /etc/profile.d/content-review.sh \
    && chmod 644 /etc/profile.d/content-review.sh

RUN printf '#!/bin/bash\n\
set -euo pipefail\n\
/usr/local/bin/start-content-review\n\
if [ \"$#\" -eq 0 ]; then\n\
  exec /bin/bash\n\
elif [ \"$#\" -eq 1 ]; then\n\
  exec /bin/bash -lc \"$1\"\n\
else\n\
  exec \"$@\"\n\
fi\n' > /usr/local/bin/content-task-entrypoint \
    && chmod 755 /usr/local/bin/content-task-entrypoint

ENTRYPOINT ["/usr/local/bin/content-task-entrypoint"]
CMD ["/bin/bash"]
