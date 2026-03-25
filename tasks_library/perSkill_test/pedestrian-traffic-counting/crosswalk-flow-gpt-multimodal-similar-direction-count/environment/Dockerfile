FROM python:3.12-slim

WORKDIR /app

RUN mkdir -p /app/output /app/crosswalk_sequences

COPY crosswalk_sequences /app/crosswalk_sequences
COPY skills /root/.codex/skills

RUN pip install --no-cache-dir \
    openai==2.15.0 \
    pytest==8.4.1
