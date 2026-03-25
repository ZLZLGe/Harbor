FROM python:3.11-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /root

RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice-calc \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir openpyxl==3.1.5 pytest==8.4.1

COPY bottling-expansion-template.xlsx /root/bottling-expansion-template.xlsx
COPY skills /root/.codex/skills
