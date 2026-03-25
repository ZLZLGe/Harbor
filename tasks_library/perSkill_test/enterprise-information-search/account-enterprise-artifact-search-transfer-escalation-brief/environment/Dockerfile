FROM python:3.12-slim

RUN pip install --no-cache-dir pytest==8.4.1

WORKDIR /root

COPY escalation_request.json /root/escalation_request.json
COPY customer_ops /root/customer_ops

COPY skills /root/.codex/skills
