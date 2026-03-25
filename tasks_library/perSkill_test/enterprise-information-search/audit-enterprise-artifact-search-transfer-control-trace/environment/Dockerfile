FROM python:3.12-slim

RUN pip install --no-cache-dir pytest==8.4.1

WORKDIR /root

COPY audit_request.json /root/audit_request.json
COPY audit_prep /root/audit_prep

COPY skills /root/.codex/skills
