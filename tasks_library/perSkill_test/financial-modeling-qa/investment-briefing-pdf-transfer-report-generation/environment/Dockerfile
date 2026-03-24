FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y python3 python3-pip \
  && pip3 install --break-system-packages reportlab==4.2.5 pypdf==5.1.0 pytest==8.4.1 \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /root

COPY portfolio_holdings.csv /root/portfolio_holdings.csv
COPY performance_attribution.csv /root/performance_attribution.csv
COPY risk_notes.json /root/risk_notes.json

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills
COPY skills /root/.factory/skills
