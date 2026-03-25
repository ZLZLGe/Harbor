FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

COPY expense_claims_bundle /root/
COPY employee_roster.csv /root/
COPY trip_approvals.json /root/
COPY policy_limits.json /root/

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills

RUN pip3 install --break-system-packages \
    pdfplumber==0.11.9 \
    pypdf==6.6.0 \
    pytest==8.4.1
