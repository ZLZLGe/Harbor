FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV WORKSPACE=/root
ENV APP_HOME=/root/report-service
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64

USER root

RUN apt-get update && apt-get install -y \
    openjdk-17-jdk \
    python3 \
    python3-venv \
    python3-pip \
    curl \
    git \
    maven \
    patch

RUN mkdir -p ${WORKSPACE}/patches ${APP_HOME}

COPY app ${APP_HOME}
COPY skills /root/.codex/skills

RUN git config --global user.email "taskbuilder@example.com" && \
    git config --global user.name "Task Builder" && \
    cd ${APP_HOME} && \
    git init && \
    git add . && \
    git commit -m "Initial vulnerable report preview service"

RUN cd ${APP_HOME} && mvn -q -DskipTests dependency:go-offline

WORKDIR ${WORKSPACE}

CMD ["/bin/bash"]
