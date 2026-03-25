FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /root

COPY data /tmp/task_data
COPY create_vendor_statement_assets.py /tmp/create_vendor_statement_assets.py
COPY skills /root/.codex/skills
COPY skills /etc/claude-code/.claude/skills

RUN pip3 install --break-system-packages \
    pdfplumber==0.11.9 \
    pypdf==6.6.0 \
    pytest==8.3.5 \
    reportlab==4.4.1

RUN mkdir -p /root/data \
    && python3 /tmp/create_vendor_statement_assets.py /tmp/task_data/statement_seed.json /root/data/vendor_statement_bundle \
    && rm -rf /tmp/task_data /tmp/create_vendor_statement_assets.py
