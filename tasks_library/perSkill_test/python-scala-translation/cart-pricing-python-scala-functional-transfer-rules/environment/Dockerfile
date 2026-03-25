FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PATH="/root/.local/share/coursier/bin:${PATH}"

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    gzip \
    openjdk-17-jdk-headless \
    python3 \
    python3-pytest \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fL https://github.com/coursier/coursier/releases/download/v2.1.25-M23/cs-x86_64-pc-linux.gz \
    | gzip -d > /usr/local/bin/cs \
    && chmod +x /usr/local/bin/cs \
    && cs install scala:2.13.12 scalac:2.13.12

WORKDIR /root

COPY cart_pricing.py /root/cart_pricing.py
COPY skills /root/.codex/skills
