FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
  libreoffice-calc \
  python3 \
  python3-openpyxl \
  python3-pytest \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /root

COPY icu_capacity_template.xlsx /root/icu_capacity_template.xlsx
RUN ln -s /root/icu_capacity_template.xlsx /root/icu_capacity_template \
  && ln -s /root/ward_capacity_model.xlsx /root/ward_capacity_model

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills
COPY skills /root/.factory/skills
