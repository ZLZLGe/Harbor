FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-openpyxl \
    python3-pytest \
    libreoffice-calc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

COPY reservoir-template.xlsx /root/reservoir-template.xlsx
COPY monthly_hydrology.csv /root/monthly_hydrology.csv
COPY water_demand.csv /root/water_demand.csv
COPY skills /root/.codex/skills
