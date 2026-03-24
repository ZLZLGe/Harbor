# Dockerfile for the reconciliation batch criteria migration task

FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV SDKMAN_DIR=/root/.sdkman

RUN apt-get update && apt-get install -y \
    curl \
    git \
    unzip \
    zip \
    wget \
    && rm -rf /var/lib/apt/lists/*

RUN curl -s "https://get.sdkman.io" | bash

RUN bash -c "source $SDKMAN_DIR/bin/sdkman-init.sh && \
    sdk install java 21.0.2-tem && \
    sdk install maven 3.9.6 && \
    sdk default java 21.0.2-tem"

ENV JAVA_HOME=/root/.sdkman/candidates/java/current
ENV MAVEN_HOME=/root/.sdkman/candidates/maven/current
ENV PATH="${JAVA_HOME}/bin:${MAVEN_HOME}/bin:${PATH}"

WORKDIR /workspace

COPY workspace/ /workspace/

COPY skills/ /root/.claude/skills/
COPY skills /root/.codex/skills
COPY skills/ /root/.codex/skills/
COPY skills/ /root/.opencode/skills/
COPY skills/ /root/.goose/skills/
COPY skills/ /root/.factory/skills/
COPY skills/ /root/.agents/skills/
COPY skills/ /root/.gemini/skills/

RUN bash -c "source $SDKMAN_DIR/bin/sdkman-init.sh && mvn -q -DskipTests dependency:go-offline" || true
RUN echo 'source /root/.sdkman/bin/sdkman-init.sh' >> /root/.bashrc
RUN mkdir -p /logs/verifier

CMD ["/bin/bash"]
