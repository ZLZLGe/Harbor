FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV NPM_CONFIG_REGISTRY=https://registry.npmjs.org/

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    nodejs \
    npm \
    tini \
    && rm -rf /var/lib/apt/lists/*

RUN /usr/bin/npm install -g @openai/codex@0.118.0

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
    numpy==2.1.3 \
    pandas==2.2.3 \
    scipy==1.14.1 \
    astropy==6.1.7 \
    requests==2.32.3 \
    pytest==8.3.3

RUN useradd -m -s /bin/bash appuser

RUN mkdir -p /root/.nvm /home/appuser/.nvm \
    && printf ':\n' > /root/.nvm/nvm.sh \
    && printf ':\n' > /home/appuser/.nvm/nvm.sh

RUN mkdir -p /services/observatory-api

WORKDIR /app
COPY data/ /app/data/
COPY hidden-service-src/server.py /services/observatory-api/server.py
COPY skills/ /opt/task-skills/

RUN set -eux; \
    mkdir -p /opt; \
    sha256sum /services/observatory-api/server.py | awk '{print $1}' > /opt/observatory-server.sha256; \
    chmod 755 /services/observatory-api/server.py

RUN mkdir -p /app/output /logs/verifier

RUN chown -R appuser:appuser /app /home/appuser /logs/verifier /services/observatory-api

ENV OBSERVATORY_API_URL=http://127.0.0.1:8124
ENV HOME=/home/appuser

RUN printf '#!/bin/bash\n\
set -euo pipefail\n\
\n\
mkdir -p \"$HOME/.codex/skills\" /app/.codex/skills\n\
if [ -d /opt/task-skills ]; then\n\
  for skill in /opt/task-skills/*; do\n\
    [ -d \"$skill\" ] || continue\n\
    name=\"$(basename \"$skill\")\"\n\
    mkdir -p \"$HOME/.codex/skills/$name\" \"/app/.codex/skills/$name\"\n\
    cp -R \"$skill/.\" \"$HOME/.codex/skills/$name/\"\n\
    cp -R \"$skill/.\" \"/app/.codex/skills/$name/\"\n\
  done\n\
fi\n\
\n\
if [ -f /app/.codex/skills/exoplanet-workflows/build_and_submit_catalog_vetting.py ]; then\n\
  ln -sf /app/.codex/skills/exoplanet-workflows/build_and_submit_catalog_vetting.py /usr/local/bin/build_and_submit_catalog_vetting\n\
  ln -sf /app/.codex/skills/exoplanet-workflows/build_and_submit_catalog_vetting.py /app/build_and_submit_catalog_vetting.py\n\
  ln -sf /app/.codex/skills/exoplanet-workflows/submit_catalog_vetting.py /app/submit_catalog_vetting.py\n\
  ln -sf /app/.codex/skills/exoplanet-workflows/probe_catalog_vetting.py /app/probe_catalog_vetting.py\n\
  chmod 755 /app/.codex/skills/exoplanet-workflows/build_and_submit_catalog_vetting.py\n\
  chmod 755 /app/.codex/skills/exoplanet-workflows/submit_catalog_vetting.py\n\
  chmod 755 /app/.codex/skills/exoplanet-workflows/probe_catalog_vetting.py\n\
  chmod 755 /usr/local/bin/build_and_submit_catalog_vetting\n\
fi\n\
\n\
if ! curl -fsS http://127.0.0.1:8124/health >/dev/null 2>&1; then\n\
  nohup python3 /services/observatory-api/server.py >/tmp/observatory-api.log 2>&1 &\n\
  for i in $(seq 1 60); do\n\
    if curl -fsS http://127.0.0.1:8124/health >/dev/null 2>&1; then\n\
      break\n\
    fi\n\
    sleep 0.5\n\
  done\n\
fi\n\
\n\
curl -fsS http://127.0.0.1:8124/health >/dev/null 2>&1 || {\n\
  echo \"Hidden observatory API failed to start\" >&2\n\
  [ -f /tmp/observatory-api.log ] && cat /tmp/observatory-api.log >&2 || true\n\
  exit 1\n\
}\n\
exec \"$@\"\n' > /usr/local/bin/astronomy-entrypoint \
    && chmod 755 /usr/local/bin/astronomy-entrypoint

RUN printf 'if [ -n \"${OBSERVATORY_API_BOOTSTRAPPED:-}\" ]; then\n\
  return 0 2>/dev/null || exit 0\n\
fi\n\
export OBSERVATORY_API_BOOTSTRAPPED=1\n\
if ! curl -fsS http://127.0.0.1:8124/health >/dev/null 2>&1; then\n\
  nohup python3 /services/observatory-api/server.py >/tmp/observatory-api.log 2>&1 &\n\
  for i in $(seq 1 40); do\n\
    if curl -fsS http://127.0.0.1:8124/health >/dev/null 2>&1; then\n\
      break\n\
    fi\n\
    sleep 0.25\n\
  done\n\
fi\n' > /etc/profile.d/observatory-bootstrap.sh \
    && chmod 644 /etc/profile.d/observatory-bootstrap.sh

USER appuser

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/astronomy-entrypoint"]
CMD ["/bin/bash"]
