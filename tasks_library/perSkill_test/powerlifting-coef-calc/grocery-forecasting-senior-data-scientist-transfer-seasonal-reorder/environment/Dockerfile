FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.local/bin:$PATH"
RUN mkdir -p /usr/local/bin
RUN curl -LsSf https://astral.sh/uv/0.9.22/install.sh | env UV_INSTALL_DIR="/usr/local/bin" sh

WORKDIR /root

RUN mkdir -p /root/data
COPY store_sales_history.xlsx /root/data/store_reorder_forecast.xlsx
COPY store-sales-readme.md /root/data/store-sales-readme.md

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills

RUN pip3 install --break-system-packages \
    pandas==2.2.3 \
    openpyxl==3.1.5 \
    pytest==8.4.1 \
    pytest-json-ctrf==0.3.5
