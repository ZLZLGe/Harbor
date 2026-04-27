FROM python:3.12-slim

WORKDIR /root

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        tini \
        ripgrep \
        curl \
        python3-rdkit \
        python3-pandas \
        python3-pytest \
    && rm -rf /var/lib/apt/lists/*

RUN ln -sf /usr/bin/python3 /usr/local/bin/python3 \
    && ln -sf /usr/bin/python3 /usr/local/bin/python

COPY data /root/workspace/data
COPY services /services
COPY skills /root/.codex/skills

RUN mkdir -p /root/workspace/output /logs/verifier \
    && chmod +x /services/safety-normalizer/server.py \
    && find /root/.codex/skills -type f -name "*.py" -exec chmod +x {} \;
