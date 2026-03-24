FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC
ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8

USER root

RUN apt-get update && apt-get install -y \
    openjdk-17-jdk \
    maven \
    python3 \
    git \
    unzip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace/release-portal

COPY project/ /workspace/release-portal/
COPY skills /root/.codex/skills
