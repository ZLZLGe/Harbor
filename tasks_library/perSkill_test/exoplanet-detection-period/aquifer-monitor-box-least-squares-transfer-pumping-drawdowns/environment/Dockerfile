FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN pip install --no-cache-dir \
    numpy==1.26.4 \
    astropy==6.1.7 \
    pytest==8.3.5

WORKDIR /root

COPY data /root/data
COPY skills /root/.codex/skills
