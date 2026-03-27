FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

RUN pip install --no-cache-dir \
    pytest==8.4.1 \
    pytest-json-ctrf==0.3.5

WORKDIR /root

COPY scene_alerts.json /root/scene_alerts.json
COPY skills /root/skills
COPY skills /root/.codex/skills
