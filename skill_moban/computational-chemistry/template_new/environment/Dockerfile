FROM debian:bookworm-slim

WORKDIR /root

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        python3 \
        python3-pip \
        python3-pytest \
        python3-rdkit \
        ripgrep \
        tini \
    && rm -rf /var/lib/apt/lists/*

COPY data /root/data
COPY skills /root/.codex/skills

RUN ln -sf /usr/bin/python3 /usr/bin/python \
    && ln -sf /usr/bin/pytest /usr/local/bin/pytest

RUN mkdir -p /root/workspace /logs/verifier
