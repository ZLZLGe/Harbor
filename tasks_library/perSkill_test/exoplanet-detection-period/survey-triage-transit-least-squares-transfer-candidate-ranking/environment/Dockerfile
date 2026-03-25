FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN pip install --no-cache-dir \
    numpy==2.1.3 \
    pandas==2.2.3 \
    pytest==8.3.5 \
    transitleastsquares==1.32

WORKDIR /root

COPY data /root/data
COPY skills /root/.codex/skills
