FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV HOME=/root
ENV BASH_ENV=/etc/frontend-slides-env.sh

WORKDIR /workspace

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        chromium \
        curl \
        fonts-dejavu-core \
        gosu \
        procps \
        tini \
    && rm -rf /var/lib/apt/lists/*

RUN pip install \
    beautifulsoup4==4.12.3 \
    playwright==1.48.0 \
    pytest==8.3.3 \
    pytest-json-ctrf==0.3.7 \
    requests==2.32.3

COPY . /opt/frontend-slides-task

RUN mkdir -p /root/data /root/output /logs/verifier /logs/agent/skills /root/.codex/skills /app/.codex/skills /services \
    && cp -R /opt/frontend-slides-task/data/. /root/data/ \
    && cp -R /opt/frontend-slides-task/hidden-service-src /services/frontend-slides-api \
    && if [ -d /opt/frontend-slides-task/skills ]; then \
         cp -R /opt/frontend-slides-task/skills/. /root/.codex/skills/; \
         cp -R /opt/frontend-slides-task/skills/. /app/.codex/skills/; \
         cp -R /opt/frontend-slides-task/skills/. /logs/agent/skills/; \
       fi \
    && python3 /opt/frontend-slides-task/build-scripts/write_protected_hashes.py \
    && chmod -R 755 /services/frontend-slides-api \
    && chmod 644 /opt/frontend-slides-task/protected_hashes.json \
    && chmod 755 /bin /usr/bin /bin/sh /bin/bash /workspace

RUN printf '#!/bin/bash\n\
set -euo pipefail\n\
\n\
mkdir -p /root/output /logs/verifier\n\
. /etc/frontend-slides-env.sh\n\
\n\
exec \"$@\"\n' > /usr/local/bin/frontend-slides-entrypoint \
    && chmod 755 /usr/local/bin/frontend-slides-entrypoint

RUN printf 'if [ -z "${FRONTEND_SLIDES_ENV_STARTED:-}" ]; then\n\
  export FRONTEND_SLIDES_ENV_STARTED=1\n\
  mkdir -p /root/output /logs/verifier\n\
  if ! curl -fsS http://127.0.0.1:8111/health >/dev/null 2>&1; then\n\
    nohup python3 /services/frontend-slides-api/server.py >/tmp/frontend-slides-api.log 2>&1 &\n\
    for i in $(seq 1 60); do\n\
      if curl -fsS http://127.0.0.1:8111/health >/dev/null 2>&1; then\n\
        break\n\
      fi\n\
      sleep 0.2\n\
    done\n\
  fi\n\
fi\n' > /etc/frontend-slides-env.sh \
    && chmod 644 /etc/frontend-slides-env.sh

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/frontend-slides-entrypoint"]
CMD ["/bin/bash"]
