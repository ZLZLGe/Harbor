FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    ca-certificates \
    curl \
    default-jdk \
    gzip \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.local/share/coursier/bin:$PATH"
RUN curl -fL https://github.com/coursier/coursier/releases/download/v2.1.25-M23/cs-x86_64-pc-linux.gz | gzip -d > cs \
    && chmod +x cs \
    && ./cs setup --yes \
    && ./cs install scala:2.13.12 scalac:2.13.12 sbt:1.12.0

WORKDIR /root
COPY EventNormalizer.py /root/
COPY localtest /root/localtest

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skills
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills
