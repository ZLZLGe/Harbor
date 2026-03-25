FROM python:3.11-slim

RUN pip install --no-cache-dir numpy==2.3.0 pandas==2.3.0

WORKDIR /root

COPY us_macro_quarterly_real_panel.csv /root/
COPY skills /root/.codex/skills
