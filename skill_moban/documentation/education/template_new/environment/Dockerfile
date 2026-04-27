FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    bash \
    ca-certificates \
    curl \
    jq \
    python3 \
    python3-pip \
    python-is-python3 \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages --no-cache-dir \
    pytest==8.3.4 \
    requests==2.32.3

WORKDIR /root

COPY . /tmp/task_environment

RUN mkdir -p /workspace/session_bundle /workspace/environment && \
    cp -R /tmp/task_environment/session_bundle/. /workspace/session_bundle/ && \
    cp /tmp/task_environment/knowledge_service.py /opt/knowledge_service.py && \
    if [ -d /tmp/task_environment/skills ]; then \
      mkdir -p /workspace/environment/skills && \
      cp -R /tmp/task_environment/skills/. /workspace/environment/skills/ && \
      mkdir -p /root/.claude/skills /root/.codex/skills /root/.opencode/skill /root/.goose/skills /root/.factory/skills /root/.agents/skills /root/.gemini/skills && \
      cp -R /tmp/task_environment/skills/. /root/.claude/skills/ && \
      cp -R /tmp/task_environment/skills/. /root/.codex/skills/ && \
      cp -R /tmp/task_environment/skills/. /root/.opencode/skill/ && \
      cp -R /tmp/task_environment/skills/. /root/.goose/skills/ && \
      cp -R /tmp/task_environment/skills/. /root/.factory/skills/ && \
      cp -R /tmp/task_environment/skills/. /root/.agents/skills/ && \
      cp -R /tmp/task_environment/skills/. /root/.gemini/skills/; \
    fi && \
    rm -rf /tmp/task_environment

RUN printf '%s\n' \
    'if ! curl -fsS http://127.0.0.1:8080/health >/dev/null 2>&1; then' \
    '  python /opt/knowledge_service.py >/tmp/knowledge_service.log 2>&1 &' \
    '  sleep 0.2' \
    'fi' \
    > /etc/profile.d/knowledge_service.sh
