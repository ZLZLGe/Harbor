FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV HOME=/root

RUN apt-get update \
    && apt-get install -y --no-install-recommends tmux xz-utils ca-certificates curl tini \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . /tmp/template-environment

RUN mkdir -p /app/data /app/output /app/runtime /app/ops /logs/agent/skills /logs/verifier \
    && cp -R /tmp/template-environment/data/. /app/data/ \
    && cp -R /tmp/template-environment/runtime_seed/. /app/runtime/ \
    && cp -R /tmp/template-environment/console/. /app/ops/ \
    && mkdir -p /app/bootstrap \
    && cp -R /tmp/template-environment/bootstrap/. /app/bootstrap/ \
    && cp /tmp/template-environment/bootstrap/task_session_bootstrap.sh /usr/local/bin/task-session-bootstrap \
    && chmod +x /app/ops/recovery-console \
    && chmod +x /app/bootstrap/bootstrap_staged_session.sh \
    && chmod +x /usr/local/bin/task-session-bootstrap \
    && mkdir -p /root/.claude/skills /root/.codex/skills /root/.opencode/skill /root/.goose/skills /root/.factory/skills /root/.agents/skills /root/.gemini/skills \
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
    && touch /root/.bash_profile \
    && grep -q 'tmux_skill_env.sh' /root/.bash_profile || printf '\nif [ -d /root/.codex/skills/tmux ] && [ -f /usr/local/share/debian-digest-recovery/tmux_skill_env.sh ]; then . /usr/local/share/debian-digest-recovery/tmux_skill_env.sh; fi\n' >> /root/.bash_profile \
    && printf '%s\n' '#!/bin/bash' \
        'set -euo pipefail' \
        '/app/bootstrap/bootstrap_staged_session.sh >/app/runtime/logs/bootstrap.log 2>&1 || true' \
        'if [ -d /root/.codex/skills/tmux ] && [ -f /usr/local/share/debian-digest-recovery/tmux_skill_env.sh ]; then . /usr/local/share/debian-digest-recovery/tmux_skill_env.sh; fi' \
        'if [ "$#" -eq 0 ]; then' \
        '  exec /bin/bash' \
        'elif [ "$#" -eq 1 ]; then' \
        '  exec /bin/bash -lc "$1"' \
        'else' \
        '  exec "$@"' \
        'fi' > /usr/local/bin/debian-digest-entrypoint \
    && chmod 755 /usr/local/bin/debian-digest-entrypoint \
    && chmod -R a+rX /app/data /app/ops /app/runtime /app/bootstrap /logs/agent/skills

ENV PYTHONPATH=/app/ops

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/debian-digest-entrypoint"]
CMD ["/bin/bash"]
