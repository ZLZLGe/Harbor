# Dockerfile for the customer profiles Spring Boot migration task

FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV SDKMAN_DIR=/root/.sdkman

RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    unzip \
    zip \
    vim \
    nano \
    && rm -rf /var/lib/apt/lists/*

RUN curl -s "https://get.sdkman.io" | bash

RUN bash -c "source $SDKMAN_DIR/bin/sdkman-init.sh && \
    sdk install java 11.0.22-tem && \
    sdk install java 21.0.2-tem && \
    sdk default java 21.0.2-tem"

RUN bash -c "source $SDKMAN_DIR/bin/sdkman-init.sh && \
    sdk install maven 3.9.6"

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

RUN bash -c "source $SDKMAN_DIR/bin/sdkman-init.sh && \
    cd /workspace/customer-profiles && \
    sdk use java 11.0.22-tem && \
    mvn -f pom.xml dependency:go-offline -B" || true

RUN echo 'source /root/.sdkman/bin/sdkman-init.sh' >> /root/.bashrc
RUN bash -c "source $SDKMAN_DIR/bin/sdkman-init.sh && sdk default java 21.0.2-tem"
RUN mkdir -p /logs/verifier

CMD ["/bin/bash"]
