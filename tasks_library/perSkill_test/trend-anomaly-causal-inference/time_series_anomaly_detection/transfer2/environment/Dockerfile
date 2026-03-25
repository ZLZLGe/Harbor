FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CMDSTAN_VERBOSE=false

RUN pip install --no-cache-dir pandas numpy prophet pytest

WORKDIR /root

COPY data /root/data
COPY skills /root/.codex/skills

CMD ["/bin/bash"]
