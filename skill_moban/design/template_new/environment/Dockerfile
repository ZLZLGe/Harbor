FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    chromium \
    curl \
    tini \
    ripgrep \
    util-linux \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash appuser

WORKDIR /app

COPY . /opt/environment-src

RUN mkdir -p /services /opt/task-skills /opt/task-seed \
    && mv /opt/environment-src/workspace /app/workspace \
    && mv /opt/environment-src/render-qa-service /services/render-qa-service \
    && if [ -d /opt/environment-src/skills ]; then \
         mv /opt/environment-src/skills /opt/task-skills; \
       else \
         mkdir -p /opt/task-skills; \
       fi \
    && if [ -d /opt/environment-src/seed ]; then \
         mv /opt/environment-src/seed /opt/task-seed; \
       else \
         mkdir -p /opt/task-seed; \
       fi \
    && rm -rf /opt/environment-src

RUN pip install \
    cython==3.0.11 \
    requests==2.32.3 \
    pytest==8.3.3 \
    pytest-json-ctrf==0.3.7 \
    setuptools \
    wheel \
    && if [ -f /services/render-qa-service/requirements.txt ]; then \
         pip install -r /services/render-qa-service/requirements.txt; \
       fi

RUN mkdir -p /tmp/render_qa_build \
    && cp /services/render-qa-service/server.py /tmp/render_qa_build/render_qa_service_hidden.py \
    && printf '%s\n' \
       'from setuptools import setup' \
       'from Cython.Build import cythonize' \
       '' \
       'setup(ext_modules=cythonize("render_qa_service_hidden.py", language_level=3))' \
       > /tmp/render_qa_build/setup.py \
    && cd /tmp/render_qa_build \
    && CC=gcc python3 setup.py build_ext --inplace \
    && export RENDER_QA_SITE_PACKAGES="$(python3 -c 'import site; print(site.getsitepackages()[0])')" \
    && install -m 755 render_qa_service_hidden*.so "$RENDER_QA_SITE_PACKAGES"/ \
    && python3 -c 'import render_qa_service_hidden; assert hasattr(render_qa_service_hidden, "main"); print("render_qa_service_hidden import ok")' \
    && rm -rf /tmp/render_qa_build \
    && mkdir -p /app/output/deck /logs/verifier \
    && if [ -f /opt/task-seed/deck/index.html ]; then \
         cp /opt/task-seed/deck/index.html /app/output/deck/index.html; \
       fi \
    && rm -rf /services/render-qa-service \
    && mkdir -p /services/render-qa-service \
    && printf 'render-qa-service source is intentionally withheld; use the localhost manifest/validate endpoints and task skill diagnostics.\\n' > /services/render-qa-service/README.txt \
    && chown -R appuser:appuser /app /home/appuser /logs /opt/task-skills /opt/task-seed /services/render-qa-service

RUN printf '%s\n' \
    '#!/usr/bin/env python3' \
    'from render_qa_service_hidden import main' \
    '' \
    'if __name__ == "__main__":' \
    '    main()' > /usr/local/bin/render-qa-launcher \
    && chmod 755 /usr/local/bin/render-qa-launcher

RUN printf '%s\n' \
    '#!/bin/bash' \
    '# Ensure task-local skills and the seeded draft are present even when Harbor launches login shells directly.' \
    'set +e' \
    'mkdir -p /logs/agent/skills /app/.codex/skills /app/output/deck' \
    'if [ -d /opt/task-skills ]; then' \
    '  for skill in /opt/task-skills/*; do' \
    '    [ -d "$skill" ] || continue' \
    '    name="$(basename "$skill")"' \
    '    if [ ! -d "/logs/agent/skills/$name" ]; then' \
    '      mkdir -p "/logs/agent/skills/$name"' \
    '      cp -R "$skill/." "/logs/agent/skills/$name/"' \
    '    fi' \
    '    if [ ! -d "/app/.codex/skills/$name" ]; then' \
    '      mkdir -p "/app/.codex/skills/$name"' \
    '      cp -R "$skill/." "/app/.codex/skills/$name/"' \
    '    fi' \
    '  done' \
    'fi' \
    'if [ ! -f /app/output/deck/index.html ] && [ -f /opt/task-seed/deck/index.html ]; then' \
    '  cp /opt/task-seed/deck/index.html /app/output/deck/index.html' \
    'fi' \
    'chown -R appuser:appuser /logs/agent /app/.codex /app/output/deck >/dev/null 2>&1 || true' \
    > /etc/profile.d/task-bootstrap.sh \
    && chmod 755 /etc/profile.d/task-bootstrap.sh

ENV HOME=/home/appuser
ENV DECK_QA_URL=http://127.0.0.1:8364
ENV PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium

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
chown -R appuser:appuser \"$HOME/.codex\" /app/.codex\n\
\n\
mkdir -p /app/output/deck\n\
if [ ! -f /app/output/deck/index.html ] && [ -f /opt/task-seed/deck/index.html ]; then\n\
  cp /opt/task-seed/deck/index.html /app/output/deck/index.html\n\
fi\n\
\n\
if ! curl -fsS http://127.0.0.1:8364/manifest >/dev/null 2>&1; then\n\
  nohup /usr/local/bin/render-qa-launcher >/tmp/render-qa-service.log 2>&1 &\n\
  for i in $(seq 1 60); do\n\
    if curl -fsS http://127.0.0.1:8364/manifest >/dev/null 2>&1; then\n\
      break\n\
    fi\n\
    sleep 0.5\n\
  done\n\
fi\n\
\n\
curl -fsS http://127.0.0.1:8364/manifest >/dev/null 2>&1 || {\n\
  echo \"render-qa-service failed to start\" >&2\n\
  [ -f /tmp/render-qa-service.log ] && cat /tmp/render-qa-service.log >&2 || true\n\
  exit 1\n\
}\n\
\n\
exec runuser -u appuser -- env \\\n\
  HOME=\"$HOME\" \\\n\
  DECK_QA_URL=\"$DECK_QA_URL\" \\\n\
  PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=\"$PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH\" \\\n\
  \"$@\"\n' > /usr/local/bin/design-entrypoint \
    && chmod 755 /usr/local/bin/design-entrypoint

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/design-entrypoint"]
CMD ["/bin/bash"]
