FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /root

RUN apt-get update \
    && apt-get install -y --no-install-recommends poppler-utils \
    && pip install --no-cache-dir \
        pillow==11.1.0 \
        pdf2image==1.17.0 \
        pypdf==5.4.0 \
        pytest==8.4.1 \
        reportlab==4.2.5

COPY skills /root/.codex/skills
COPY incident_builder /tmp/incident_builder

RUN mkdir -p /root/incident_packet \
    && python3 /tmp/incident_builder/write_response_payload.py /root/incident_packet/response_payload.json \
    && python3 /tmp/incident_builder/build_incident_form.py /root/incident_packet/terminal_incident_form.pdf \
    && rm -rf /tmp/incident_builder
