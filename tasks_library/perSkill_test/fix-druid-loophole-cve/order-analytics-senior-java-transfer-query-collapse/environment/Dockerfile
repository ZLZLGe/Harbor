FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV WORKSPACE=/workspace
ENV APP_HOME=/workspace/order-analytics
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64

USER root

RUN apt-get update && apt-get install -y \
    openjdk-17-jdk \
    python3 \
    python3-pytest \
    maven \
    git \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p ${APP_HOME}

COPY app ${APP_HOME}
COPY skills /root/.codex/skills

RUN cd ${APP_HOME} && mvn -q -DskipTests package

WORKDIR ${APP_HOME}

CMD ["/bin/bash"]
