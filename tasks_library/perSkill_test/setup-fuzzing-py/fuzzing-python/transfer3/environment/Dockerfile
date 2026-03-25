FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1             PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir pytest

WORKDIR /root

COPY files/root /root
COPY skills /root/.codex/skills

CMD ["/bin/bash"]
