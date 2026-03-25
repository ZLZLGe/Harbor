FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir uv

WORKDIR /root

COPY workspaces /root/workspaces
COPY skills /root/.codex/skills

CMD ["/bin/bash"]
