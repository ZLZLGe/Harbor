FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir \
    numpy==2.2.4 \
    openai==2.15.0 \
    pytest==8.4.1

COPY input /app/input
RUN mkdir -p /app/output

COPY skills /root/.codex/skills
