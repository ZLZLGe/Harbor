FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    curl \
    nodejs \
    npm \
    tini \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir pytest==8.4.1 pytest-json-ctrf==0.3.5
RUN npm install -g @openai/codex@0.120.0

COPY . /tmp/environment/

RUN mkdir -p /root/data /root/artifacts /root/output /root/app /app /app/skills \
    /root/.claude/skills /root/.codex/skills /root/.opencode/skill /root/.goose/skills \
    /root/.factory/skills /root/.agents/skills /root/.gemini/skills /logs/agent/skills /logs/verifier \
    && cp -R /tmp/environment/data/. /root/data/ \
    && cp -R /tmp/environment/artifacts/. /root/artifacts/ \
    && cp -R /tmp/environment/app/. /root/app/ \
    && cp -R /tmp/environment/app/. /app/ \
    && if [ -d /tmp/environment/skills ]; then \
        cp -R /tmp/environment/skills/. /logs/agent/skills/; \
        cp -R /tmp/environment/skills/. /app/skills/; \
        cp -R /tmp/environment/skills/. /root/.claude/skills/; \
        cp -R /tmp/environment/skills/. /root/.codex/skills/; \
        cp -R /tmp/environment/skills/. /root/.opencode/skill/; \
        cp -R /tmp/environment/skills/. /root/.goose/skills/; \
        cp -R /tmp/environment/skills/. /root/.factory/skills/; \
        cp -R /tmp/environment/skills/. /root/.agents/skills/; \
        cp -R /tmp/environment/skills/. /root/.gemini/skills/; \
    fi \
    && chmod 755 /root \
    && chmod -R a+rX /root/data /root/artifacts /root/app /app /root/.codex/skills /logs/agent/skills \
    && chmod 777 /root/output \
    && rm -rf /tmp/environment

WORKDIR /app

ENTRYPOINT ["/bin/bash", "-lc"]
CMD ["exec /bin/bash"]
