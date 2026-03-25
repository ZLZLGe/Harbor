FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /root

RUN pip install --no-cache-dir \
    defusedxml==0.7.1 \
    pytest==8.4.1

COPY sales-overview-draft.pptx /root/sales-overview-draft.pptx
COPY skills /root/.codex/skills
