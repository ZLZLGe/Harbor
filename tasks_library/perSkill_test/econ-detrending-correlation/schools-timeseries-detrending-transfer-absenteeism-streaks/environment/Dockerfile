FROM python:3.11-slim

RUN pip install --no-cache-dir \
    numpy==2.3.0 \
    pandas==2.3.0 \
    pytest==8.4.1

WORKDIR /root

COPY district_attendance.sqlite /root/
COPY skills /root/.codex/skills
