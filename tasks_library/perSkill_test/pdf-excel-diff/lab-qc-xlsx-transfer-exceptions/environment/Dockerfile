FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /root

COPY skills /root/.codex/skills
COPY generate_lab_qc_workbook.py /tmp/generate_lab_qc_workbook.py

RUN pip install --no-cache-dir \
    openpyxl==3.1.5 \
    pytest==8.4.1 \
    && python /tmp/generate_lab_qc_workbook.py \
    && rm /tmp/generate_lab_qc_workbook.py
