FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir pytest

WORKDIR /root

COPY project_dump /root/project_dump
COPY data /root/data
COPY skills /root/.codex/skills

CMD ["/bin/bash"]
