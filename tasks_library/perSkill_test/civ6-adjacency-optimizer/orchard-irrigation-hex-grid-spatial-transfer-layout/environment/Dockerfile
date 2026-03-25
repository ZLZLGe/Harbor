FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /root

RUN pip install --no-cache-dir pytest==8.3.5

COPY data/ /data/
COPY skills /root/skills
COPY skills /root/.codex/skills

RUN mkdir -p /output

CMD ["/bin/bash"]
