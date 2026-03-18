FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive

RUN set -eux; \
    success=0; \
    for attempt in 1 2 3; do \
      if apt-get update -o Acquire::Retries=3 && \
         apt-get install -y --no-install-recommends python3 python3-yaml ca-certificates; then \
        success=1; \
        break; \
      fi; \
      echo "apt attempt ${attempt} failed, retrying" >&2; \
      sleep 5; \
    done; \
    if [ "$success" -ne 1 ]; then \
      echo "apt installation failed" >&2; \
      exit 1; \
    fi; \
    rm -rf /var/lib/apt/lists/*

WORKDIR /root

COPY configs /root/configs

COPY skills /root/.codex/skills
COPY skills /root/.claude/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills
