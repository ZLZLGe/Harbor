FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-openpyxl \
    python3-pytest \
    libreoffice-calc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

COPY gradebook_template.xlsx /root/gradebook_template.xlsx
COPY makeup_scores.csv /root/makeup_scores.csv
COPY skills /root/.codex/skills
