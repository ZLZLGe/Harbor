FROM python:3.11-slim

WORKDIR /root

RUN pip install --no-cache-dir pytest==8.4.1

COPY workspace/ /root/workspace/
COPY skills /root/.codex/skills

CMD ["python3", "--version"]
