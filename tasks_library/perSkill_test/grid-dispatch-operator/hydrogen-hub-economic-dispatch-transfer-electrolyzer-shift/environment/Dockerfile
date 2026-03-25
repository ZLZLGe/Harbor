FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /root

RUN pip install --no-cache-dir pytest==8.3.5 PyYAML==6.0.2

COPY shift_requirements.yaml /root/shift_requirements.yaml
COPY electrolyzer_fleet.csv /root/electrolyzer_fleet.csv
COPY skills /root/.codex/skills
