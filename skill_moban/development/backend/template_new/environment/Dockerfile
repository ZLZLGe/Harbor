FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV GATEWAY_PORT=8080
ENV RATE_SERVICE_URL=http://127.0.0.1:9101
ENV BOOKING_SERVICE_URL=http://127.0.0.1:9102

WORKDIR /app/workspace

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl procps ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && pip install flask requests pytest

COPY workspace /app/workspace
COPY skills /root/.codex/skills
COPY skills /logs/agent/skills

RUN mkdir -p /logs/verifier /tmp/shipping-api \
    && chmod 755 /app/workspace/run.sh \
    && find /app/workspace/data -type f -print0 | sort -z | xargs -0 sha256sum > /opt/shipping-api-data.sha256 \
    && find /app/workspace/contracts -type f -print0 | sort -z | xargs -0 sha256sum > /opt/shipping-api-contracts.sha256 \
    && find /app/workspace/services -type f -print0 | sort -z | xargs -0 sha256sum > /opt/shipping-api-services.sha256 \
    && chmod 644 /opt/shipping-api-data.sha256 /opt/shipping-api-contracts.sha256 /opt/shipping-api-services.sha256

CMD ["/bin/bash"]
