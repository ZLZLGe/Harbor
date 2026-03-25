FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    libreoffice-calc \
    python3 \
    python3-openpyxl \
    python3-pytest \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

RUN mkdir -p /root/data
COPY course_gradebook_template.xlsx /root/data/course_gradebook_template.xlsx

COPY skills /root/.codex/skills
