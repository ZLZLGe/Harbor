FROM python:3.11-slim

RUN pip install --no-cache-dir \
    numpy==1.26.4 \
    pandas==2.2.1 \
    netCDF4==1.6.5 \
    pytest==8.1.1

WORKDIR /root

COPY data /root/data
COPY config /root/config
COPY skills /root/.codex/skills

RUN mkdir -p /root/reports
