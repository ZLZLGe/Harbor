FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV BRANDROOM_PORT=8137

WORKDIR /app

RUN mkdir -p /root/brandroom/input /root/brandroom/output /root/.codex/skills /logs/agent/skills /logs/verifier /var/log/brandroom /services/brandroom-archive

COPY data /root/brandroom/input
COPY hidden-service-src/server.py /services/brandroom-archive/server.py
COPY skills /root/.codex/skills
COPY skills /logs/agent/skills

RUN sha256sum /services/brandroom-archive/server.py | awk '{print $1}' > /opt/brandroom-server.sha256 \
    && find /root/brandroom/input -type f -print0 | sort -z | xargs -0 sha256sum > /opt/brandroom-input.sha256 \
    && chmod 755 /services/brandroom-archive/server.py \
    && chmod 644 /opt/brandroom-server.sha256 /opt/brandroom-input.sha256 \
    && chmod 777 /var/log/brandroom /root/brandroom/output

RUN printf '#!/bin/bash\n\
set -euo pipefail\n\
\n\
if ! python3 -c '"'"'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8137/health", timeout=1).read()'"'"' >/dev/null 2>&1; then\n\
  nohup python3 /services/brandroom-archive/server.py >/tmp/brandroom-archive.log 2>&1 &\n\
  for i in $(seq 1 60); do\n\
    if python3 -c '"'"'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8137/health", timeout=1).read()'"'"' >/dev/null 2>&1; then\n\
      break\n\
    fi\n\
    sleep 0.5\n\
  done\n\
fi\n\
\n\
python3 -c '"'"'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8137/health", timeout=1).read()'"'"' >/dev/null 2>&1 || {\n\
  echo "brandroom archive service failed to start" >&2\n\
  [ -f /tmp/brandroom-archive.log ] && cat /tmp/brandroom-archive.log >&2 || true\n\
  exit 1\n\
}\n\
\n' > /usr/local/bin/start-brandroom-archive \
    && chmod 755 /usr/local/bin/start-brandroom-archive

RUN printf '#!/bin/bash\n\
set -euo pipefail\n\
/usr/local/bin/start-brandroom-archive\n\
if [ "$#" -eq 0 ]; then\n\
  exec /bin/bash\n\
elif [ "$#" -eq 1 ]; then\n\
  exec /bin/bash -lc "$1"\n\
else\n\
  exec "$@"\n\
fi\n' > /usr/local/bin/brandroom-entrypoint \
    && chmod 755 /usr/local/bin/brandroom-entrypoint

ENTRYPOINT ["/usr/local/bin/brandroom-entrypoint"]
CMD ["/bin/bash"]
