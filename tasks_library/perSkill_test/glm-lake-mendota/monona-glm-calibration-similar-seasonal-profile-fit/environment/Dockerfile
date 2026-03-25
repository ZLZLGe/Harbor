FROM --platform=linux/amd64 ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-numpy \
    python3-pandas \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

COPY glm /usr/local/bin/glm
RUN chmod +x /usr/local/bin/glm

COPY glm3.nml /root/glm3.nml
COPY inputs /root/inputs

RUN mkdir -p /root/output /root/results

COPY skills /root/.codex/skills
