FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

RUN pip install --no-cache-dir \
    pytest==8.4.1 \
    pyyaml==6.0.3 \
    pyperplan==2.1 \
    unified-planning==1.3.0 \
    up-pyperplan==1.1.0

WORKDIR /root

COPY survey_batch.json /root/survey_batch.json
COPY survey_cases /root/survey_cases
COPY plan_batch.py /root/plan_batch.py
COPY skills /root/skills
COPY skills /root/.codex/skills
