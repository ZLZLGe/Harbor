FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    coreutils \
    curl \
    jq \
    procps \
    python3 \
    python-is-python3 \
    python3-pytest \
    python3-yaml \
    ripgrep \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /root/app /root/data /root/output /root/.codex/skills /logs/agent/skills /logs/verifier

COPY app /root/app
COPY data /root/data
COPY skills /app/skills
COPY skills /root/.codex/skills
COPY skills /logs/agent/skills

RUN find /root/data -type f -print0 | sort -z | xargs -0 sha256sum > /opt/payment-input.sha256 \
    && chmod 644 /opt/payment-input.sha256 \
    && chmod 755 /root /tmp /bin /bin/sh /bin/bash \
    && chmod -R a+rX /root/app /root/data /root/.codex/skills /logs/agent/skills \
    && chmod 777 /root/output /logs/verifier

CMD ["/bin/bash"]
