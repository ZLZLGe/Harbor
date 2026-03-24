FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV WORKSPACE=/root
ENV APP_DIR=/root/plugin-manifest-importer
ENV PATCHES_DIR=/root/patches
ENV MANIFEST_DIR=/root/manifests
ENV OUTPUT_DIR=/root/import-output
ENV RUNTIME_ARTIFACTS_DIR=/root/runtime-artifacts
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64

USER root

RUN apt-get update && apt-get install -y \
    openjdk-17-jdk \
    maven \
    git \
    python3 \
    procps \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p ${APP_DIR} ${PATCHES_DIR} ${MANIFEST_DIR} ${OUTPUT_DIR} ${RUNTIME_ARTIFACTS_DIR}

COPY plugin-manifest-importer ${APP_DIR}
COPY manifests ${MANIFEST_DIR}

RUN cd ${APP_DIR} && \
    git init && \
    git config user.name "Harbor Builder" && \
    git config user.email "builder@example.com" && \
    git add . && \
    git commit -m "Baseline vulnerable plugin manifest importer" && \
    mvn -q -DskipTests package

COPY skills /root/.codex/skills

WORKDIR ${WORKSPACE}

CMD ["/bin/bash"]
