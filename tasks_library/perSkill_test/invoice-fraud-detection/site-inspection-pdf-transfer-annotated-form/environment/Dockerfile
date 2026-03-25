FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

COPY inspection_form.pdf /root/
COPY inspection_answers.json /root/
COPY skills /root/.codex/skills

RUN pip install --no-cache-dir --break-system-packages \
    pypdf==6.6.0 \
    pdf2image==1.17.0 \
    pillow==11.3.0 \
    reportlab==4.4.7 \
    pytest==8.4.1
