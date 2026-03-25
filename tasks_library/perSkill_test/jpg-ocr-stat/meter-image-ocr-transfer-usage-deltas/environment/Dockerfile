FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    Pillow==12.0.0 \
    pytesseract==0.3.13 \
    pytest==8.4.1

COPY workspace /app/workspace
WORKDIR /app/workspace

COPY skills /root/.codex/skills
