FROM python:3.11-slim

WORKDIR /root

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        tini \
        curl \
        ca-certificates \
        unzip \
        ripgrep \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir \
        numpy \
        pandas \
        scikit-learn \
        pytest

RUN mkdir -p /tmp/wheels \
    && curl -L --retry 8 --retry-delay 5 --max-time 1200 \
        "https://download.pytorch.org/whl/cpu/torch-2.5.1%2Bcpu-cp311-cp311-linux_x86_64.whl" \
        -o /tmp/wheels/torch-2.5.1+cpu-cp311-cp311-linux_x86_64.whl \
    && python -m pip install --no-cache-dir /tmp/wheels/torch-2.5.1+cpu-cp311-cp311-linux_x86_64.whl \
    && rm -rf /tmp/wheels

RUN mkdir -p /tmp/codex \
    && curl -L --retry 8 --retry-delay 5 --max-time 1200 \
        "https://registry.npmjs.org/@openai/codex/-/codex-0.120.0-linux-x64.tgz" \
        -o /tmp/codex/codex.tgz \
    && tar -xzf /tmp/codex/codex.tgz -C /tmp/codex \
    && install -m 0755 \
        /tmp/codex/package/vendor/x86_64-unknown-linux-musl/codex/codex \
        /usr/local/bin/codex \
    && codex --version \
    && rm -rf /tmp/codex

COPY . /root/environment

RUN python /root/environment/generate_seed_data.py \
    && mkdir -p /root/.codex \
    && if [ -d /root/environment/skills ]; then cp -a /root/environment/skills /root/.codex/skills; fi \
    && chmod +x /root/environment/project/run_pipeline.py \
    && mkdir -p /root/answer
