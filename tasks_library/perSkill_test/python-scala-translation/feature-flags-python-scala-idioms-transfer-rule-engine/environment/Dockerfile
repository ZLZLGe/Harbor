FROM eclipse-temurin:17-jdk-jammy

ENV DEBIAN_FRONTEND=noninteractive
ENV PATH="/root/.local/share/coursier/bin:${PATH}"

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    gzip \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fL https://github.com/coursier/coursier/releases/download/v2.1.25-M23/cs-x86_64-pc-linux.gz \
    | gzip -d > /usr/local/bin/cs \
    && chmod +x /usr/local/bin/cs \
    && cs install scala:2.13.12 scalac:2.13.12 sbt:1.10.2

RUN pip3 install --no-cache-dir pytest==8.3.5

WORKDIR /root

COPY FeatureFlagEngine.py /root/FeatureFlagEngine.py
COPY flag_cases.json /root/flag_cases.json
COPY scala_feature_flags /root/scala_feature_flags
COPY skills /root/.codex/skills

RUN cd /root/scala_feature_flags && sbt -batch update
