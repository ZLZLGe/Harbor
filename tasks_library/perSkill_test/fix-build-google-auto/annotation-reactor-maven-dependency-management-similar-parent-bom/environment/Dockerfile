FROM maven:3.9.6-eclipse-temurin-17

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pytest \
    && rm -rf /var/lib/apt/lists/*

COPY skills /root/.codex/skills
COPY project /workspace/annotation-parent

WORKDIR /workspace/annotation-parent
