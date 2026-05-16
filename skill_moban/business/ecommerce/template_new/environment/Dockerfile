FROM node:20-bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV WORKSPACE_ROOT=/app/workspace
ENV DATA_ROOT=/app/data
ENV PATH=/app/workspace/bin:${PATH}

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    jq \
    python3 \
    python3-pip \
    ripgrep \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --break-system-packages beautifulsoup4==4.12.3

WORKDIR /app

COPY data /app/data
COPY workspace /app/workspace
COPY skills /tmp/task-skills

RUN mkdir -p /app/workspace/out \
    /app/workspace/.codex/skills \
    /app/workspace/.agents/skills \
    /root/.codex/skills \
    /root/.agents/skills \
    /logs/verifier \
  && chmod +x /app/workspace/build_preview.sh /app/workspace/bin/shopify \
  && if [ -d /tmp/task-skills ]; then \
       cp -R /tmp/task-skills/. /app/workspace/.codex/skills/; \
       cp -R /tmp/task-skills/. /app/workspace/.agents/skills/; \
       cp -R /tmp/task-skills/. /root/.codex/skills/; \
       cp -R /tmp/task-skills/. /root/.agents/skills/; \
     fi \
  && cd /app/workspace \
  && npm ci \
  && rm -rf /tmp/task-skills \
  && find /app/data -type f -print0 | sort -z | xargs -0 sha256sum > /opt/task-data.sha256

WORKDIR /app/workspace

CMD ["/bin/bash"]
