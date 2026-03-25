FROM maven:3.9.9-eclipse-temurin-21

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pytest \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY workspace/ /workspace/
COPY skills /root/.codex/skills

RUN mkdir -p /logs/verifier && mvn -q -DskipTests dependency:go-offline || true

CMD ["/bin/bash"]
