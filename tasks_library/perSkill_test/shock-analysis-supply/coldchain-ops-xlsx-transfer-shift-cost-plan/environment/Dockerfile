FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    libreoffice \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages \
    openpyxl==3.1.5 \
    pytest==8.4.1

WORKDIR /root

COPY coldchain-ops-template.xlsx /root/coldchain-ops-template.xlsx
COPY store_daily_demand.csv /root/store_daily_demand.csv
COPY warehouse_shifts.csv /root/warehouse_shifts.csv
COPY equipment_power_curve.csv /root/equipment_power_curve.csv
COPY tou_tariff_template.csv /root/tou_tariff_template.csv
COPY skills /root/.codex/skills
