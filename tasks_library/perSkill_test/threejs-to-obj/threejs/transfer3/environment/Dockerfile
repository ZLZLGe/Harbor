FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PATH="/opt/node/bin:${PATH}"
ENV NODE_VERSION="v20.19.0"

RUN python3 -m pip install --no-cache-dir \
        numpy==2.1.3 \
        pytest==8.4.1 \
    && python3 - <<'PY'
import os
import urllib.request

version = os.environ["NODE_VERSION"]
url = f"https://nodejs.org/dist/{version}/node-{version}-linux-x64.tar.gz"
urllib.request.urlretrieve(url, "/tmp/node.tar.gz")
PY

RUN mkdir -p /opt/node \
    && tar -xzf /tmp/node.tar.gz -C /opt/node --strip-components=1 \
    && rm /tmp/node.tar.gz \
    && node --version \
    && npm --version

WORKDIR /root

RUN mkdir -p /root/data /root/output /root/ground_truth

RUN npm init -y \
    && npm pkg set type=module \
    && npm install three@0.175.0

COPY data/service_cart.js /root/data/service_cart.js

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills
COPY skills /root/.github/skills
