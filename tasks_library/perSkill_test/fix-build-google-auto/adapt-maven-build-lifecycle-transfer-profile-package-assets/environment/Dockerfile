FROM maven:3.9.8-eclipse-temurin-17

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    && rm -rf /var/lib/apt/lists/*

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills

WORKDIR /workspace

COPY project/ /workspace/

RUN mvn -q -B -f app/pom.xml -Pproduction dependency:go-offline
