FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /root

RUN pip install --no-cache-dir pytest==8.3.5

COPY station_request.toml /root/station_request.toml
COPY boiler_fleet.csv /root/boiler_fleet.csv
COPY skills /root/.codex/skills
