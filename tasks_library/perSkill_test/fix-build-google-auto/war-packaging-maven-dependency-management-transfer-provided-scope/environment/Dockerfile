FROM maven:3.9.6-eclipse-temurin-17

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pytest \
    && rm -rf /var/lib/apt/lists/*

COPY skills /root/.codex/skills
COPY vendor-src /tmp/vendor-src
RUN mvn --batch-mode -q -f /tmp/vendor-src/portal-bootstrap/pom.xml -DskipTests install

COPY project /workspace/web-portal

WORKDIR /workspace/web-portal
