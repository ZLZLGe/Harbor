FROM python:3.12-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN python -m pip install --no-cache-dir \
    pytest==8.3.5 \
    pyyaml==6.0.2 \
    requests==2.32.3

RUN apt-get update \
    && apt-get install -y --no-install-recommends nodejs npm \
    && rm -rf /var/lib/apt/lists/*

RUN node --version \
    && npm --version \
    && npm install -g @openai/codex@0.120.0 \
    && codex --version

COPY . /tmp/task-environment

RUN mkdir -p /root/data /root/workspace /root/output /root/.codex/skills /logs/agent/skills /logs/verifier /opt/task-baselines \
    && cp -R /tmp/task-environment/data/. /root/data/ \
    && cp -R /tmp/task-environment/workspace/. /root/workspace/ \
    && if [ -d /tmp/task-environment/skills ]; then cp -R /tmp/task-environment/skills/. /root/.codex/skills/; fi \
    && if [ -d /tmp/task-environment/skills ]; then cp -R /tmp/task-environment/skills/. /logs/agent/skills/; fi \
    && find /root/data -type f -print0 | sort -z | xargs -0 sha256sum | sed 's#  /root/data/#  #' > /opt/task-baselines/data.sha256 \
    && if [ -d /root/.codex/skills/axiom ]; then cd /root/.codex/skills/axiom && find . -type f -print0 | sort -z | xargs -0 sha256sum | sed 's#  \\./#  #' > /opt/task-baselines/axiom-skill.sha256; else printf '' > /opt/task-baselines/axiom-skill.sha256; fi \
    && chmod 755 /root /tmp /bin /bin/sh /bin/bash \
    && chmod -R a+rwX /root/workspace /root/output /logs \
    && chmod -R a+rX /root/data /root/.codex/skills /logs/agent/skills \
    && chmod 755 /root/workspace/build_decision_packet.py \
    && rm -rf /tmp/task-environment

CMD ["/bin/bash"]
