FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    tini \
    ca-certificates \
    git \
    nodejs \
    npm \
    ripgrep \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    numpy==1.26.4 \
    pandas==2.2.2 \
    scikit-learn==1.5.2 \
    rdkit-pypi==2022.9.5 \
    pytest==8.4.1 \
    pytest-json-ctrf==0.3.5

RUN mkdir -p /root/data /root/output /root/workspace/data /root/workspace/output /root/workspace/workbench \
    /logs/verifier /app/data /app/output \
    /root/.claude/skills /root/.codex/skills /root/.opencode/skill /root/.goose/skills /root/.factory/skills /root/.agents/skills /root/.gemini/skills /app/skills

COPY . /tmp/environment/
COPY skills /app/skills
COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills

RUN pip install --no-cache-dir /tmp/environment/workbench/unimol_tools_cli \
    && cp -R /tmp/environment/data/. /root/workspace/data/ \
    && cp -R /tmp/environment/data/. /root/data/ \
    && cp -R /tmp/environment/data/. /app/data/ \
    && cp -R /tmp/environment/workbench/. /root/workspace/workbench/ \
    && if [ -d /app/skills/cli-anything-unimol-tools/helpers ]; then \
          mkdir -p /root/workspace/workbench/release_tools; \
          cp -R /app/skills/cli-anything-unimol-tools/helpers/. /root/workspace/workbench/release_tools/; \
          find /root/workspace/workbench/release_tools -type f -name '*.sh' -exec chmod +x {} +; \
    fi \
    && rm -rf /root/workspace/workbench/unimol_tools_cli \
    && chmod 755 /root \
    && chmod -R a+rX /root/workspace /root/data /app/skills \
    && chmod 777 /root/output /root/workspace/output /app/output \
    && rm -rf /tmp/environment

ENV DATA_DIR=/root/workspace/data
ENV OUTPUT_DIR=/root/workspace/output
ENV UNIMOL_WORKBENCH_ROOT=/root/workspace/workbench

WORKDIR /root/workspace

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/bin/bash"]
