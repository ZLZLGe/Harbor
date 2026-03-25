FROM python:3.11-slim

WORKDIR /root

ENV PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir \
    pandas==2.2.3 \
    pytest==8.4.1

COPY data /root/mine_inputs
COPY skills /root/.codex/skills
