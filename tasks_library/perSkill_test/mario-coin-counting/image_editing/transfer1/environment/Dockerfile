FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1

RUN set -eux; \
    for attempt in 1 2 3 4 5; do \
      apt-get update || true; \
      if apt-get -o Acquire::Retries=3 install -y --no-install-recommends --fix-missing imagemagick; then \
        break; \
      fi; \
      if [ "$attempt" -eq 5 ]; then \
        echo "apt install imagemagick failed after retries" >&2; \
        exit 1; \
      fi; \
      rm -rf /var/lib/apt/lists/*; \
      sleep 5; \
    done; \
    rm -rf /var/lib/apt/lists/*

WORKDIR /root

COPY skills /root/skills
COPY skills /root/.codex/skills
COPY coin.png /root/coin.png
COPY enemy.png /root/enemy.png
COPY turtle.png /root/turtle.png
