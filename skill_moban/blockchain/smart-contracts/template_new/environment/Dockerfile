FROM node:20-bookworm

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    BASH_ENV=/etc/codex-command-hint.sh

WORKDIR /root

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    findutils \
    curl \
    git \
    jq \
    python3 \
    python3-pytest \
    python3-yaml \
    python-is-python3 \
    tini \
    && rm -rf /var/lib/apt/lists/*

RUN ln -sf /bin/bash /bin/sh \
    && chmod 755 /bin/sh /bin/bash /usr/bin/tini

RUN mkdir -p /opt/task-env/spec /opt/task-env/workspace /opt/task-env/skills \
    /root/workspace /root/.codex/skills /root/workspace/out /logs/agent/skills /logs/verifier

COPY data/spec /opt/task-env/spec
COPY workspace /opt/task-env/workspace
COPY skills /opt/task-env/skills

RUN cp -R /opt/task-env/spec /root/workspace/spec \
    && cp -R /opt/task-env/workspace/. /root/workspace/ \
    && if [ -d /opt/task-env/skills ]; then cp -R /opt/task-env/skills/. /root/.codex/skills/; fi \
    && if [ -d /opt/task-env/skills ]; then cp -R /opt/task-env/skills/. /logs/agent/skills/; fi \
    && cd /root/workspace \
    && npm install \
    && find /root/workspace/spec -type f -print0 | sort -z | xargs -0 sha256sum > /opt/defi-spec.sha256 \
    && if [ -d /root/.codex/skills/defi-protocol-templates ]; then \
         find /root/.codex/skills/defi-protocol-templates -type f -print0 | sort -z | xargs -0 sha256sum > /opt/defi-skill.sha256; \
       fi \
    && chmod -R a+rX /root/workspace /root/.codex/skills /logs/agent/skills \
    && chmod -R a+rwX /root/workspace/out /logs

RUN printf '%s\n' \
  'if [ -f /root/.codex/skills/defi-protocol-templates/SKILL.md ]; then' \
  '  export DEFI_PROTOCOL_TEMPLATES_HOME=/root/.codex/skills/defi-protocol-templates' \
  '  echo "[defi-protocol-templates] installed skill found at /root/.codex/skills/defi-protocol-templates" >&2' \
  '  echo "[defi-protocol-templates] inspect SKILL.md for staking, AMM, and governance templates before implementing the workspace." >&2' \
  'fi' > /etc/codex-command-hint.sh \
  && cp /etc/codex-command-hint.sh /etc/profile.d/defi-protocol-templates.sh
