FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    ca-certificates \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages \
    pytest==8.3.5 \
    playwright==1.52.0 \
    requests==2.32.3 \
    && python3 -m playwright install --with-deps chromium

COPY . /tmp/environment-context

RUN mkdir -p \
    /root/environment \
    /root/.claude/skills \
    /root/.codex/skills \
    /root/.opencode/skill \
    /root/.goose/skills \
    /root/.factory/skills \
    /root/.agents/skills \
    /root/.gemini/skills \
    /root/answer \
    /logs/verifier && \
    cp -R /tmp/environment-context/data /root/environment/data && \
    cp -R /tmp/environment-context/deck /root/environment/deck && \
    cp -R /tmp/environment-context/services /services && \
    if [ -d /tmp/environment-context/skills ] && [ "$(ls -A /tmp/environment-context/skills 2>/dev/null)" ]; then \
      cp -R /tmp/environment-context/skills/. /root/.claude/skills/ && \
      cp -R /tmp/environment-context/skills/. /root/.codex/skills/ && \
      cp -R /tmp/environment-context/skills/. /root/.opencode/skill/ && \
      cp -R /tmp/environment-context/skills/. /root/.goose/skills/ && \
      cp -R /tmp/environment-context/skills/. /root/.factory/skills/ && \
      cp -R /tmp/environment-context/skills/. /root/.agents/skills/ && \
      cp -R /tmp/environment-context/skills/. /root/.gemini/skills/ ; \
    fi && \
    rm -rf /tmp/environment-context

WORKDIR /root
