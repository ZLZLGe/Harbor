FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /root

RUN pip install --no-cache-dir pytest==8.4.1

RUN mkdir -p /root/data /root/results
COPY data /root/data
COPY skills /root/.codex/skills
