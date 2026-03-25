FROM maven:3.9.9-eclipse-temurin-17

ENV DEBIAN_FRONTEND=noninteractive
ENV WORKSPACE=/workspace

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    git \
    patch \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --break-system-packages --no-cache-dir \
    pytest==8.4.1 \
    requests==2.32.3

RUN mkdir -p /workspace /workspace/patches /opt/task-assets

COPY admin-import-service /opt/task-assets/admin-import-service-pristine
COPY import-packages /workspace/import-packages
COPY skills /root/.codex/skills

RUN cp -r /opt/task-assets/admin-import-service-pristine /workspace/admin-import-service && \
    cd /workspace/admin-import-service && \
    git init && \
    git config user.name "Task Builder" && \
    git config user.email "taskbuilder@example.com" && \
    git add . && \
    git commit -m "baseline vulnerable import service"

WORKDIR /workspace

CMD ["/bin/bash"]
