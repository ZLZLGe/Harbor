FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

WORKDIR /root

COPY data /tmp/task_data
COPY create_intake_assets.py /tmp/create_intake_assets.py
COPY skills /root/.codex/skills
COPY skills /etc/claude-code/.claude/skills

RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages \
    pypdf==6.6.0 \
    pdf2image==1.17.0 \
    pillow==11.1.0 \
    pytest==8.3.5

RUN mkdir -p /root/data \
    && python3 /tmp/create_intake_assets.py /tmp/task_data/patient_payload.json /root/data/clinic_intake_form \
    && cp /tmp/task_data/patient_payload.json /root/data/patient_payload.json \
    && rm -rf /tmp/task_data /tmp/create_intake_assets.py
