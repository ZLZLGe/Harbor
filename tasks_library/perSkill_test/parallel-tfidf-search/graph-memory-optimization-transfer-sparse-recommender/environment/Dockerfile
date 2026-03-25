FROM python:3.11-slim

RUN pip install --no-cache-dir pytest==8.4.1

WORKDIR /root

COPY workspace/ /root/workspace/
COPY skills /root/.codex/skills

CMD ["python", "--version"]
