FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir --retries 10 --timeout 120 \
    pypdf==4.0.0

COPY paper1.pdf paper2.pdf paper3.pdf /root/
COPY skills /root/.codex/skills

WORKDIR /root
