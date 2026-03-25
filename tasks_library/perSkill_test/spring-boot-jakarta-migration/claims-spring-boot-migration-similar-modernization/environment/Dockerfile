FROM maven:3.9.9-eclipse-temurin-21

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    && python3 -m pip install --break-system-packages --no-cache-dir pytest==8.4.1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY workspace/ /workspace/
COPY skills /root/.codex/skills

RUN mkdir -p /logs/verifier

CMD ["/bin/bash"]
