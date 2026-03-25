FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PATH="/root/.local/share/coursier/bin:${PATH}"

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    openjdk-17-jdk-headless \
    curl \
    ca-certificates \
    gzip \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages pytest==8.3.5

RUN curl -fL https://github.com/coursier/coursier/releases/download/v2.1.25-M23/cs-x86_64-pc-linux.gz | gzip -d > /usr/local/bin/cs \
    && chmod +x /usr/local/bin/cs \
    && cs install sbt

WORKDIR /root

COPY event_normalizer.py /root/
COPY challenge /root/challenge
COPY localtest /root/localtest
COPY skills /root/.codex/skills

RUN mkdir -p /root/challenge/output \
    && cd /root/localtest \
    && sbt -batch update
