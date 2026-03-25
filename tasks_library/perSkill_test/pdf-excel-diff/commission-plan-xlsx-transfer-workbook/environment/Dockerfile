FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    libreoffice-calc \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages \
    openpyxl==3.1.5 \
    pytest==8.3.5

WORKDIR /root

COPY sales_detail_2026Q1.xlsx /root/sales_detail_2026Q1.xlsx
COPY team_quota_plan_2026.xlsx /root/team_quota_plan_2026.xlsx
COPY skills /root/.codex/skills
