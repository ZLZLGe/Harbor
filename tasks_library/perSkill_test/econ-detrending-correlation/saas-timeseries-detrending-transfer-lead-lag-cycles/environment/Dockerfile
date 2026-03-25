FROM python:3.11-slim

RUN pip install --no-cache-dir \
    numpy==2.3.0 \
    pandas==2.3.0 \
    pytest==8.4.1 \
    statsmodels==0.14.4

WORKDIR /root

COPY monthly_saas_marketing.csv /root/
COPY skills /root/.codex/skills
