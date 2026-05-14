FROM python:3.12-slim

WORKDIR /root

ENV DEBIAN_FRONTEND=noninteractive \
    HOME=/root \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        nodejs \
        npm \
        ripgrep \
        tini \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    astropy==6.1.7 \
    numpy==1.26.4 \
    pandas==2.2.3 \
    pytest==8.3.5 \
    scipy==1.15.2

COPY . /root/environment
COPY skills /root/.codex/skills
COPY skills /logs/agent/skills

RUN mkdir -p \
      /root/.codex/skills \
      /root/environment/pipeline \
      /root/answer \
      /logs/agent/skills \
    && cp -R /root/environment/workspace/. /root/environment/pipeline/ \
    && chmod +x /root/environment/pipeline/build_m101_review.py
