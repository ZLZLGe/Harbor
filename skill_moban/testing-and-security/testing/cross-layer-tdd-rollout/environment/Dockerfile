FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      python3 \
      python3-pip; \
    rm -rf /var/lib/apt/lists/*

COPY workspace /app/workspace
WORKDIR /app/workspace

COPY environment/skills /root/.claude/skills
COPY environment/skills /root/.codex/skills
COPY environment/skills /root/.opencode/skill
COPY environment/skills /root/.goose/skills
COPY environment/skills /root/.factory/skills
COPY environment/skills /root/.agents/skills
COPY environment/skills /root/.gemini/skills
