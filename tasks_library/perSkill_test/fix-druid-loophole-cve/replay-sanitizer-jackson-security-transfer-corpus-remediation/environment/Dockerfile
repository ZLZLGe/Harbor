FROM maven:3.9.9-eclipse-temurin-17

ENV DEBIAN_FRONTEND=noninteractive
ENV WORKSPACE=/workspace

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pytest \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /workspace /opt/task-assets

COPY replay-sanitizer-src /workspace/replay-sanitizer
COPY replay-sanitizer-src /opt/task-assets/replay-sanitizer-pristine
COPY historical-corpus /workspace/historical-corpus
COPY skills /root/.codex/skills

WORKDIR /workspace

CMD ["/bin/bash"]
