FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    tini \
    && rm -rf /var/lib/apt/lists/* \
    && chmod 755 /bin /bin/sh /bin/bash /tmp

RUN pip install --no-cache-dir pandas==2.2.2 numpy==1.26.4 pytest==8.4.1 pytest-json-ctrf==0.3.5

RUN mkdir -p /root/data /root/output /app/data /app/output

COPY . /tmp/environment/

RUN cp -R /tmp/environment/data/. /root/data/ \
    && cp -R /tmp/environment/data/. /app/data/ \
    && mkdir -p /app/skills /root/.claude/skills /root/.codex/skills /root/.opencode/skill /root/.goose/skills /root/.factory/skills /root/.agents/skills /root/.gemini/skills \
    && if [ -d /tmp/environment/skills ]; then \
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
    && chmod -R a+rX /root/data /app/data /app/skills \
    && chmod 777 /root/output /app/output \
    && rm -rf /tmp/environment

WORKDIR /app

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/bin/bash"]
