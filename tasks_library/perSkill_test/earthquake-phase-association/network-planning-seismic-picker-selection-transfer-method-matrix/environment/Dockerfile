FROM python:3.11-slim

WORKDIR /root

ENV PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir pytest==8.4.1

COPY data /root/planning_inputs
COPY skills /root/.codex/skills
