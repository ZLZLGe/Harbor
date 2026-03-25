FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /root

RUN pip install --no-cache-dir \
    pillow==11.1.0 \
    pytest==8.4.1 \
    python-pptx==1.0.2

COPY incident-brief.json /root/incident-brief.json
COPY brand-guide.md /root/brand-guide.md
COPY skills /root/.codex/skills
