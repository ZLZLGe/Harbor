FROM python:3.11-slim

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir \
    numpy==2.1.3 \
    pandas==2.2.3 \
    netCDF4==1.7.2 \
    pytest==8.3.5

WORKDIR /root

RUN mkdir -p /root/data /root/config /root/reports

COPY data/blue_heron_output.nc /root/data/blue_heron_output.nc
COPY config/refuge_rules.toml /root/config/refuge_rules.toml
COPY skills /root/.codex/skills
