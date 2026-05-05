FROM node:22-bookworm

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8
ENV HOME=/root

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 bash coreutils findutils grep sed gawk ca-certificates tini curl ripgrep \
    && npm install -g @openai/codex@0.120.0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . /tmp/template-environment

RUN mkdir -p /app/bin /app/data /app/output /root/.claude/skills /root/.codex/skills /root/.opencode/skill /root/.goose/skills /root/.factory/skills /root/.agents/skills /root/.gemini/skills /logs/agent/skills /logs/verifier \
    && cp -R /tmp/template-environment/bin/. /app/bin/ \
    && cp -R /tmp/template-environment/data/. /app/data/ \
    && chmod +x /app/bin/rebuild_airport_reports.sh /app/bin/steps/*.sh \
    && if [ -d /tmp/template-environment/skills ]; then \
        cp -R /tmp/template-environment/skills/. /root/.claude/skills/; \
        cp -R /tmp/template-environment/skills/. /root/.codex/skills/; \
        cp -R /tmp/template-environment/skills/. /root/.opencode/skill/; \
        cp -R /tmp/template-environment/skills/. /root/.goose/skills/; \
        cp -R /tmp/template-environment/skills/. /root/.factory/skills/; \
        cp -R /tmp/template-environment/skills/. /root/.agents/skills/; \
        cp -R /tmp/template-environment/skills/. /root/.gemini/skills/; \
        cp -R /tmp/template-environment/skills/. /logs/agent/skills/; \
      fi \
    && chmod -R a+rX /app /logs/agent/skills

RUN printf '%s\n' '#!/bin/bash' \
    'set -euo pipefail' \
    'if [ "$#" -eq 0 ]; then' \
    '  exec /bin/bash' \
    'elif [ "$#" -eq 1 ]; then' \
    '  exec /bin/bash -lc "$1"' \
    'else' \
    '  exec "$@"' \
    'fi' > /usr/local/bin/scripting-airports-entrypoint \
    && chmod 755 /usr/local/bin/scripting-airports-entrypoint

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/scripting-airports-entrypoint"]
CMD ["/bin/bash"]
