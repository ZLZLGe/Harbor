FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV WORKSPACE=/root
ENV SERVICE_DIR=/root/preview-service
ENV PATCHES_DIR=/root/patches
ENV PREVIEW_PORT=8080
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64

USER root

RUN apt-get update && apt-get install -y \
    openjdk-17-jdk \
    maven \
    git \
    curl \
    python3 \
    procps \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p ${PATCHES_DIR} ${SERVICE_DIR}

COPY preview-service ${SERVICE_DIR}

RUN cd ${SERVICE_DIR} && \
    git init && \
    git config user.name "Harbor Builder" && \
    git config user.email "builder@example.com" && \
    git add . && \
    git commit -m "Baseline vulnerable preview service" && \
    mvn -q -DskipTests package

COPY skills /root/.codex/skills

WORKDIR ${WORKSPACE}

CMD ["/bin/bash"]
