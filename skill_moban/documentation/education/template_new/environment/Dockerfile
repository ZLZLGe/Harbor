FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV HOME=/home/appuser

RUN apt-get update && apt-get install -y --no-install-recommends \
    gosu \
    tini \
    ripgrep \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash appuser

WORKDIR /app

COPY . /tmp/task-env

RUN pip install \
    pandas==2.2.3 \
    matplotlib==3.9.2 \
    pyyaml==6.0.2 \
    nbformat==5.10.4 \
    nbclient==0.10.0 \
    ipykernel==6.29.5 \
    pytest==8.3.3

RUN mkdir -p /app/workspace /app/.codex/skills /home/appuser/.codex/skills \
    && cp -R /tmp/task-env/workspace/. /app/workspace/ \
    && if [ -d /tmp/task-env/skills ]; then cp -R /tmp/task-env/skills/. /app/.codex/skills/; fi \
    && if [ -d /tmp/task-env/skills ]; then cp -R /tmp/task-env/skills/. /home/appuser/.codex/skills/; fi \
    && rm -rf /tmp/task-env

RUN mkdir -p /app/output /logs/verifier \
    && chown -R appuser:appuser /app /home/appuser /logs/verifier

RUN printf '#!/bin/bash\n\
set -euo pipefail\n\
\n\
mkdir -p \"$HOME/.codex/skills\" /app/.codex/skills\n\
exec gosu appuser \"$@\"\n' > /usr/local/bin/education-entrypoint \
    && chmod 755 /usr/local/bin/education-entrypoint

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/education-entrypoint"]
CMD ["/bin/bash"]
