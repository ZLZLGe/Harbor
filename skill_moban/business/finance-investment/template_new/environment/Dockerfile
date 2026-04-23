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
COPY skills /app/.codex/skills
COPY skills /home/appuser/.codex/skills
COPY skills /root/.codex/skills
COPY skills /root/.claude/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills
COPY skills /root/.factory/skills

RUN pip install \
    pandas==2.2.3 \
    numpy==2.1.3 \
    requests==2.32.3 \
    pytest==8.3.3 \
    pytest-json-ctrf==0.3.7

RUN mkdir -p /app/output /logs/verifier \
    && sha256sum /app/data/reference/company_universe.csv /app/data/reference/methodology.md /app/data/reference/source_manifest.json > /opt/public-data-reference.sha256 \
    && find /app/data/sec_companyfacts /app/data/prices /app/data/fred -type f -print0 | sort -z | xargs -0 sha256sum >> /opt/public-data-reference.sha256 \
    && chown -R appuser:appuser /app /home/appuser /logs/verifier \
    && chmod 644 /opt/public-data-reference.sha256

RUN printf '#!/bin/bash\n\
set -euo pipefail\n\
mkdir -p /app/output /logs/verifier \"$HOME/.codex/skills\" /app/.codex/skills\n\
exec gosu appuser \"$@\"\n' > /usr/local/bin/finance-investment-entrypoint \
    && chmod 755 /usr/local/bin/finance-investment-entrypoint

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/finance-investment-entrypoint"]
CMD ["/bin/bash"]
