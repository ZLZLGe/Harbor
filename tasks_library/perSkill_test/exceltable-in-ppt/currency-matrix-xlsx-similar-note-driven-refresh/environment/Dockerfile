FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    libreoffice-calc \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages \
    openpyxl==3.1.5 \
    pytest==8.4.1

WORKDIR /root

COPY fx_matrix.xlsx /root/fx_matrix.xlsx
COPY skills /root/.codex/skills
