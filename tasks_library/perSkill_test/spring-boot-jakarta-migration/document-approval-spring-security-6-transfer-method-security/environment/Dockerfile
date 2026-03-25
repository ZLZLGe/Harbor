FROM maven:3.9.9-eclipse-temurin-21

ENV DEBIAN_FRONTEND=noninteractive
ENV PIP_BREAK_SYSTEM_PACKAGES=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    && python3 -m pip install --no-cache-dir pytest==8.4.1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY workspace/ /workspace/
COPY skills /root/.codex/skills

RUN mvn -q -DskipTests dependency:go-offline

CMD ["/bin/bash"]
