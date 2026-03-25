FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /root

RUN pip install --no-cache-dir pytest==8.3.5

COPY balancing_area_portfolio.json /root/balancing_area_portfolio.json
COPY skills /root/.codex/skills
