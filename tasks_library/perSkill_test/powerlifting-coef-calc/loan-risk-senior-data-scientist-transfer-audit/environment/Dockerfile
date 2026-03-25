FROM python:3.12-slim

WORKDIR /root

RUN pip install --no-cache-dir numpy==2.2.4 pandas==2.2.3

RUN mkdir -p /root/data /root/results

COPY loan_scoring_cases.csv /root/data/loan_scoring_cases.csv
COPY skills /root/.codex/skills
