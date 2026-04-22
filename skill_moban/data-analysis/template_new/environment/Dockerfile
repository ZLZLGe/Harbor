FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV HOME=/home/appuser
ENV AUDIT_API_URL=http://127.0.0.1:8321

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gosu \
    tini \
    ripgrep \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash appuser

WORKDIR /app

COPY data /app/data
COPY hidden-service-src/server.py /opt/board-audit-build/server.py
COPY hidden-service-src/audit_impl.py /opt/board-audit-build/audit_impl.py
COPY skills /app/.codex/skills
COPY skills /home/appuser/.codex/skills

RUN pip install \
    pandas==2.2.3 \
    numpy==2.1.3 \
    requests==2.32.3 \
    pytest==8.3.3 \
    pytest-json-ctrf==0.3.7

RUN mkdir -p /app/output /logs/verifier /services/board-audit \
    && python3 -c "from pathlib import Path; import base64, marshal; build_root = Path('/opt/board-audit-build'); server_template = (build_root / 'server.py').read_text(encoding='utf-8'); audit_source = (build_root / 'audit_impl.py').read_text(encoding='utf-8'); code = compile(audit_source, 'audit_impl.py', 'exec'); payload = base64.b64encode(marshal.dumps(code)).decode('ascii'); (Path('/services/board-audit') / 'server.py').write_text(server_template.replace('__BOARD_AUDIT_EMBEDDED_IMPL_B64__', payload), encoding='utf-8')" \
    && rm -rf /opt/board-audit-build \
    && sha256sum /services/board-audit/server.py | awk '{print $1}' > /opt/board-audit-server.sha256 \
    && chown -R appuser:appuser /app /home/appuser /logs/verifier \
    && chown -R root:root /services/board-audit /opt/board-audit-server.sha256 \
    && chmod 750 /services/board-audit \
    && chmod 700 /services/board-audit/server.py \
    && chmod 600 /opt/board-audit-server.sha256

RUN printf '#!/bin/bash\n\
set -euo pipefail\n\
\n\
mkdir -p \"$HOME/.codex/skills\" /app/.codex/skills\n\
if ! curl -fsS http://127.0.0.1:8321/health >/dev/null 2>&1; then\n\
  nohup python3 /services/board-audit/server.py >/tmp/board-audit.log 2>&1 &\n\
  for i in $(seq 1 60); do\n\
    if curl -fsS http://127.0.0.1:8321/health >/dev/null 2>&1; then\n\
      break\n\
    fi\n\
    sleep 0.5\n\
  done\n\
fi\n\
\n\
curl -fsS http://127.0.0.1:8321/health >/dev/null 2>&1 || {\n\
  echo \"board-audit failed to start\" >&2\n\
  [ -f /tmp/board-audit.log ] && cat /tmp/board-audit.log >&2 || true\n\
  exit 1\n\
}\n\
\n\
exec gosu appuser \"$@\"\n' > /usr/local/bin/data-analysis-entrypoint \
    && chmod 755 /usr/local/bin/data-analysis-entrypoint

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/data-analysis-entrypoint"]
CMD ["/bin/bash"]
