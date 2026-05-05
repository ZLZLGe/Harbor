FROM node:20-bookworm

ENV DEBIAN_FRONTEND=noninteractive
ENV APP_ROOT=/app
ENV DATA_ROOT=/app/data
ENV WORKSPACE_ROOT=/app/workspace

WORKDIR /app

RUN apt-get update \
  && apt-get install -y --no-install-recommends python3 unzip zip ca-certificates git ripgrep \
  && rm -rf /var/lib/apt/lists/*

COPY . /opt/task-env

RUN mkdir -p /app/data /app/workspace /app/workspace/output /logs/agent /logs/verifier /root/.codex/skills \
  && cp -R /opt/task-env/data/. /app/data/ \
  && cp -R /opt/task-env/workspace/. /app/workspace/ \
  && if [ -d /opt/task-env/skills ]; then \
       cp -R /opt/task-env/skills/. /root/.codex/skills/ && \
       mkdir -p /logs/agent/skills && \
       cp -R /opt/task-env/skills/. /logs/agent/skills/; \
     fi \
  && cd /app/workspace/extension \
  && npm install --silent \
  && sha256sum /app/data/briefing_request.json /app/data/releases/*.json /app/data/locales/en/briefing_terms.json /app/data/locales/pt-br/briefing_terms.json /app/data/locales/zh-cn/briefing_terms.json > /opt/release-briefing-inputs.sha256

ENTRYPOINT ["/bin/bash"]
