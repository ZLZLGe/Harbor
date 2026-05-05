FROM ubuntu:24.04

WORKDIR /root

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        python-is-python3 \
        python3-pandas \
        python3-numpy \
        python3-scipy \
        python3-pytest \
        tini \
        ripgrep \
        sqlite3 \
    && rm -rf /var/lib/apt/lists/*

COPY . /root/environment

RUN python /root/environment/generate_seed_data.py \
    && mkdir -p /root/.codex \
    && if [ -d /root/environment/skills ]; then cp -a /root/environment/skills /root/.codex/skills; fi \
    && chmod +x /root/workspace/run_analysis.py

