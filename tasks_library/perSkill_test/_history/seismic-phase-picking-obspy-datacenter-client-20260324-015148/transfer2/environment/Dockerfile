FROM python:3.11-slim

WORKDIR /root

ENV PIP_INDEX_URL=https://pypi.org/simple
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

RUN python -m pip install --no-cache-dir             obspy==1.4.1             pytest==8.4.1             pytest-json-ctrf==0.3.5

COPY data /root/data
COPY requests /root/requests
COPY tools /root/tools

COPY skills /root/.claude/skills
COPY skills /etc/claude-code/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills
