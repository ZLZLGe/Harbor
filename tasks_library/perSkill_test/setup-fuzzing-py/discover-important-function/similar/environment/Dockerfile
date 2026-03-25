FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /root

COPY repos /root/repos
COPY skills /root/.codex/skills

CMD ["/bin/bash"]
