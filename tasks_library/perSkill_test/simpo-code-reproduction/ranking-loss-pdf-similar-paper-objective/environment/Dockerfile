FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /root

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-numpy \
    python3-pytest \
    poppler-utils \
    qpdf \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --break-system-packages --no-cache-dir \
    pypdf \
    pdf2image \
    pypdfium2 \
    pdfplumber \
    reportlab \
    pillow \
    pytesseract \
    pandas \
    openpyxl

COPY rankbench /root/rankbench
COPY skills /root/.codex/skills
