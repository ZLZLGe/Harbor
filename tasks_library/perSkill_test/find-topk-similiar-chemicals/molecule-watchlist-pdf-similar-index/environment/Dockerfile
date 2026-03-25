FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /root

COPY data /root/data
COPY skills /root/.codex/skills
COPY skills /etc/claude-code/.claude/skills

RUN pip3 install --break-system-packages \
    pypdf==5.4.0 \
    pytest==8.3.5
