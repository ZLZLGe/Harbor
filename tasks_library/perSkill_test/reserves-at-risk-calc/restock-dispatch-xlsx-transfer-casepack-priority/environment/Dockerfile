FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice-calc \
    libreoffice-script-provider-python \
    python3-uno \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

RUN mkdir -p /root/data /root/output

COPY restock_planner.xlsx /root/data/restock_planner.xlsx
COPY skills /root/.codex/skills

RUN pip install --no-cache-dir \
    openpyxl==3.1.5 \
    pytest==8.4.1
