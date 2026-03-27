FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/root/packages

RUN pip install --no-cache-dir atheris pytest

WORKDIR /root

COPY packages /root/packages
COPY inputs /root/inputs
COPY skills /root/.codex/skills

CMD ["/bin/bash"]
