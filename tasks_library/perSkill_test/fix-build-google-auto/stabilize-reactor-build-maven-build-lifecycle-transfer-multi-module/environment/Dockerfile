FROM maven:3.9.9-eclipse-temurin-17

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pytest \
    && rm -rf /var/lib/apt/lists/*

COPY skills /root/.codex/skills
COPY project /workspace/reactor-release-console

WORKDIR /workspace/reactor-release-console
