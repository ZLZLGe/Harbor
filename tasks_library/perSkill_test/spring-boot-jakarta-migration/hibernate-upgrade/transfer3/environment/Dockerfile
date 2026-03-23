FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends             openjdk-21-jdk-headless             python3             ca-certificates             && rm -rf /var/lib/apt/lists/*

WORKDIR /root

COPY workspace/ /workspace/

COPY skills/ /root/.claude/skills/
COPY skills/ /root/.codex/skills/
COPY skills/ /root/.opencode/skills/
COPY skills/ /root/.goose/skills/
COPY skills/ /root/.factory/skills/
COPY skills/ /root/.agents/skills/
COPY skills/ /root/.gemini/skills/

ENTRYPOINT []
CMD ["bash", "-lc", "sleep infinity"]
