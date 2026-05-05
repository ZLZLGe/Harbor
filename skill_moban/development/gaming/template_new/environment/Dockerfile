FROM mcr.microsoft.com/devcontainers/javascript-node:1-20-bookworm

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV HOME=/home/user
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

RUN apt-get update -o Acquire::Retries=5 \
    && apt-get install -y --no-install-recommends --fix-missing -o Acquire::Retries=5 \
    ca-certificates \
    curl \
    fonts-dejavu-core \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    python3-pip \
    ripgrep \
    tini \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

RUN node --version \
    && npm --version \
    && npm install -g @openai/codex@0.120.0 \
    && REAL_CODEX_BIN="$(command -v codex)" \
    && ln -sf "$REAL_CODEX_BIN" /usr/local/bin/codex-real \
    && printf '%s\n' '#!/bin/bash' \
      'set -euo pipefail' \
      'SOURCE_SKILL_HOME="${HARBOR_SKILL_SOURCE:-/home/user/.codex/skills}"' \
      'CODEX_SKILL_HOME="${CODEX_HOME:-$HOME/.codex}/skills"' \
      'mkdir -p "$CODEX_SKILL_HOME"' \
      'if [ "$CODEX_SKILL_HOME" != "$SOURCE_SKILL_HOME" ] && [ -d "$SOURCE_SKILL_HOME" ]; then' \
      '  cp -R "$SOURCE_SKILL_HOME"/. "$CODEX_SKILL_HOME"/' \
      'fi' \
      'exec /usr/local/bin/codex-real "$@"' > /usr/local/bin/codex \
    && chmod 755 /usr/local/bin/codex \
    && /usr/local/bin/codex --version

RUN mkdir -p /ms-playwright \
    && python3 -m pip install --break-system-packages \
    pytest==8.3.5 \
    playwright==1.52.0 \
    requests==2.32.3 \
    && python3 -m playwright install chromium

WORKDIR /app
COPY . /tmp/environment-context

RUN mkdir -p \
      /app/data \
      /app/workspace \
      /tests \
      /root/.claude/skills \
      /root/.codex/skills \
      /root/.opencode/skill \
      /root/.goose/skills \
      /root/.factory/skills \
      /root/.agents/skills \
      /root/.gemini/skills \
      /root/.cache \
      /home/user/.claude/skills \
      /home/user/.codex/skills \
      /home/user/.opencode/skill \
      /home/user/.goose/skills \
      /home/user/.factory/skills \
      /home/user/.agents/skills \
      /home/user/.gemini/skills \
      /home/user/.cache \
      /logs/agent/skills \
      /logs/verifier \
    && cp -R /tmp/environment-context/data/. /app/data/ \
    && cp -R /tmp/environment-context/workspace/. /app/workspace/ \
    && cp -R /tmp/environment-context/verifier/. /tests/ \
    && if [ -d /tmp/environment-context/skills ] && [ "$(ls -A /tmp/environment-context/skills 2>/dev/null)" ]; then \
      cp -R /tmp/environment-context/skills/. /root/.claude/skills/ && \
      cp -R /tmp/environment-context/skills/. /root/.codex/skills/ && \
      cp -R /tmp/environment-context/skills/. /root/.opencode/skill/ && \
      cp -R /tmp/environment-context/skills/. /root/.goose/skills/ && \
      cp -R /tmp/environment-context/skills/. /root/.factory/skills/ && \
      cp -R /tmp/environment-context/skills/. /root/.agents/skills/ && \
      cp -R /tmp/environment-context/skills/. /root/.gemini/skills/ && \
      cp -R /tmp/environment-context/skills/. /home/user/.claude/skills/ && \
      cp -R /tmp/environment-context/skills/. /home/user/.codex/skills/ && \
      cp -R /tmp/environment-context/skills/. /home/user/.opencode/skill/ && \
      cp -R /tmp/environment-context/skills/. /home/user/.goose/skills/ && \
      cp -R /tmp/environment-context/skills/. /home/user/.factory/skills/ && \
      cp -R /tmp/environment-context/skills/. /home/user/.agents/skills/ && \
      cp -R /tmp/environment-context/skills/. /home/user/.gemini/skills/ && \
      cp -R /tmp/environment-context/skills/. /logs/agent/skills/ ; \
    fi \
    && find /app/data -type f -print0 | sort -z | xargs -0 sha256sum > /opt/kanto-atlas-data.sha256 \
    && if [ -d /root/.codex/skills ] && [ "$(find /root/.codex/skills -type f | wc -l)" -gt 0 ]; then \
      find /root/.codex/skills -type f -print0 | sort -z | xargs -0 sha256sum > /opt/kanto-atlas-skills.sha256 ; \
    else \
      : > /opt/kanto-atlas-skills.sha256 ; \
    fi \
    && ln -sfn /ms-playwright /root/.cache/ms-playwright \
    && ln -sfn /ms-playwright /home/user/.cache/ms-playwright \
    && chown -R 1001:1001 /home/user /app/workspace /tests /logs /ms-playwright \
    && chmod a+rx /root /root/.cache /root/.claude /root/.codex /root/.opencode /root/.goose /root/.factory /root/.agents /root/.gemini \
    && chmod -R a+rX \
      /app/data \
      /ms-playwright \
      /root/.claude \
      /root/.codex \
      /root/.opencode \
      /root/.goose \
      /root/.factory \
      /root/.agents \
      /root/.gemini \
      /home/user/.claude \
      /home/user/.codex \
      /home/user/.opencode \
      /home/user/.goose \
      /home/user/.factory \
      /home/user/.agents \
      /home/user/.gemini \
      /logs/agent/skills \
      /opt/kanto-atlas-data.sha256 \
      /opt/kanto-atlas-skills.sha256 \
    && chmod -R u+rwX,go+rX /app/workspace /tests /logs /home/user \
    && rm -rf /tmp/environment-context

RUN printf '%s\n' '#!/bin/bash' \
    'set -euo pipefail' \
    'if [ "$#" -eq 0 ]; then' \
    '  exec /bin/bash' \
    'elif [ "$#" -eq 1 ]; then' \
    '  exec /bin/bash -lc "$1"' \
    'else' \
    '  exec "$@"' \
    'fi' > /usr/local/bin/gaming-entrypoint \
    && chmod 755 /usr/local/bin/gaming-entrypoint

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/gaming-entrypoint"]
CMD ["/bin/bash"]
