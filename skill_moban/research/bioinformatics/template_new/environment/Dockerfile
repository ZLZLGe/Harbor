FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV MPLBACKEND=Agg
ENV PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple

RUN apt-get update && apt-get install -y \
    build-essential \
    g++ \
    gcc \
    gfortran \
    curl \
    git \
    libopenblas-dev \
    liblapack-dev \
    nodejs \
    npm \
    ripgrep \
    && rm -rf /var/lib/apt/lists/*

RUN printf '%s\n' \
    '#!/bin/bash' \
    'if [ "${1:-}" = "-o-" ] && [ "${2:-}" = "https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.2/install.sh" ]; then' \
    '  printf "%s\\n" "#!/bin/bash" "mkdir -p \\"\\$HOME/.nvm\\"" "printf '\''nvm() { return 0; }\\n'\'' > \\"\\$HOME/.nvm/nvm.sh\\""' \
    '  exit 0' \
    'fi' \
    'exec /usr/bin/curl "$@"' \
    > /usr/local/bin/curl \
    && chmod +x /usr/local/bin/curl

RUN pip install --no-cache-dir \
    statsmodels==0.14.4 \
    pydeseq2==0.5.4 \
    pytest==8.4.2 \
    pytest-json-ctrf==0.3.5

COPY codex_vendor_split /opt/codex_vendor_split

RUN cat /opt/codex_vendor_split/codex.part.* > /usr/local/bin/codex \
    && chmod +x /usr/local/bin/codex \
    && printf '%s\n' \
    '#!/bin/bash' \
    'if [ "${1:-}" = "install" ] && [ "${2:-}" = "-g" ] && [ "${3:-}" = "@openai/codex@0.120.0" ]; then' \
    '  exit 0' \
    'fi' \
    'exec /usr/bin/npm "$@"' \
    > /usr/local/bin/npm \
    && chmod +x /usr/local/bin/npm \
    && codex --version

WORKDIR /root

COPY data /root/environment/data
COPY skills /root/environment/skills
COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills
