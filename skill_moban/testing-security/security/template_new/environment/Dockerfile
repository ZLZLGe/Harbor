FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV ORDERHUB_PORT=8142

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl nodejs npm \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g @openai/codex@0.120.0

COPY . /opt/orderhub-env

RUN mkdir -p /services/orderhub-api /root/.codex/skills /logs/agent/skills /root/output /logs/verifier /var/log/orderhub-api \
    && cp -R /opt/orderhub-env/data/. /root/data/ \
    && cp -R /opt/orderhub-env/hidden-service-src/. /services/orderhub-api/ \
    && if [ -d /opt/orderhub-env/skills ]; then cp -R /opt/orderhub-env/skills/. /root/.codex/skills/; fi \
    && if [ -d /opt/orderhub-env/skills ]; then cp -R /opt/orderhub-env/skills/. /logs/agent/skills/; fi \
    && find /root/data -type f -print0 | sort -z | xargs -0 sha256sum > /opt/orderhub-data.sha256 \
    && find /services/orderhub-api -type f -name '*.py' -print0 | sort -z | xargs -0 sha256sum > /opt/orderhub-service.sha256 \
    && if [ -d /root/.codex/skills ] && find /root/.codex/skills -type f | grep -q .; then find /root/.codex/skills -type f -print0 | sort -z | xargs -0 sha256sum > /opt/orderhub-skills.sha256; else : > /opt/orderhub-skills.sha256; fi \
    && chmod -R 755 /services/orderhub-api \
    && chmod 644 /opt/orderhub-data.sha256 /opt/orderhub-service.sha256 /opt/orderhub-skills.sha256 \
    && chmod 777 /var/log/orderhub-api /root/output /logs/verifier

RUN printf '#!/bin/bash\n\
set -euo pipefail\n\
\n\
if ! python3 -c '"'"'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8142/health", timeout=1).read()'"'"' >/dev/null 2>&1; then\n\
  nohup python3 /services/orderhub-api/server.py >/tmp/orderhub-api.log 2>&1 &\n\
  for i in $(seq 1 60); do\n\
    if python3 -c '"'"'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8142/health", timeout=1).read()'"'"' >/dev/null 2>&1; then\n\
      break\n\
    fi\n\
    sleep 0.5\n\
  done\n\
fi\n\
\n\
python3 -c '"'"'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8142/health", timeout=1).read()'"'"' >/dev/null 2>&1 || {\n\
  echo \"orderhub api failed to start\" >&2\n\
  [ -f /tmp/orderhub-api.log ] && cat /tmp/orderhub-api.log >&2 || true\n\
  exit 1\n\
}\n' > /usr/local/bin/start-orderhub-api \
    && chmod 755 /usr/local/bin/start-orderhub-api

RUN printf '#!/bin/bash\n\
set -euo pipefail\n\
/usr/local/bin/start-orderhub-api\n\
if [ "$#" -eq 0 ]; then\n\
  exec /bin/bash\n\
elif [ "$#" -eq 1 ]; then\n\
  exec /bin/bash -lc "$1"\n\
else\n\
  exec "$@"\n\
fi\n' > /usr/local/bin/orderhub-entrypoint \
    && chmod 755 /usr/local/bin/orderhub-entrypoint

ENTRYPOINT ["/usr/local/bin/orderhub-entrypoint"]
CMD ["/bin/bash"]
