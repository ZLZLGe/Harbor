FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV TASK_ROOT=/app/workspace

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-venv \
        curl \
        jq \
        git \
        ripgrep \
        nodejs \
        npm \
        ca-certificates \
        locales \
        postgresql \
        postgresql-client \
        postgresql-contrib \
        unzip \
    && locale-gen en_US.UTF-8 \
    && rm -rf /var/lib/apt/lists/*

ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8

COPY workspace /app/workspace
COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills
COPY skills /logs/agent/skills

RUN chmod +x /app/workspace/bin/*.sh \
    && mkdir -p /app/workspace/output /logs/agent

RUN printf '#!/bin/bash\n\
set -euo pipefail\n\
cd /app/workspace\n\
./bin/start_postgres.sh >/dev/null\n\
if [ \"$#\" -eq 0 ]; then\n\
  exec /bin/bash\n\
elif [ \"$#\" -eq 1 ]; then\n\
  exec /bin/bash -lc \"$1\"\n\
else\n\
  exec \"$@\"\n\
fi\n' > /usr/local/bin/database-tools-entrypoint \
    && chmod 755 /usr/local/bin/database-tools-entrypoint

ENTRYPOINT ["/usr/local/bin/database-tools-entrypoint"]
CMD ["/bin/bash"]
