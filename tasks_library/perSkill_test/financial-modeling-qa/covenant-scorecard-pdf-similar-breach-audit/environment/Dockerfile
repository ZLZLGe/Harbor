FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y python3 python3-pip \
  && pip3 install --break-system-packages pandas==2.2.3 openpyxl==3.1.5 pypdf==5.1.0 \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /root

COPY covenant_package.pdf /root/covenant_package.pdf
COPY quarterly_financials.xlsx /root/quarterly_financials.xlsx

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills
COPY skills /root/.factory/skills
