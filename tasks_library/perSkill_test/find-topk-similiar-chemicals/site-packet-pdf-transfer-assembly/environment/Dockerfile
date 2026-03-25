FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /root

COPY data /tmp/task_data
COPY create_site_packet_assets.py /tmp/create_site_packet_assets.py
COPY skills /root/.codex/skills
COPY skills /etc/claude-code/.claude/skills

RUN pip3 install --break-system-packages \
    pypdf==6.1.1 \
    reportlab==4.4.1 \
    pytest==8.3.5

RUN mkdir -p /root/data \
    && python3 /tmp/create_site_packet_assets.py /tmp/task_data /root/data \
    && rm -rf /tmp/task_data /tmp/create_site_packet_assets.py
