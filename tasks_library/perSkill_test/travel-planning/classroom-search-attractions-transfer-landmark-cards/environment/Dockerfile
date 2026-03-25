FROM python:3.11-slim

RUN pip install --no-cache-dir pandas==2.2.3 pytest==8.4.1

RUN mkdir -p /app/data /app/output /app/skills

COPY data/ /app/data/
COPY skills/ /app/skills/
COPY skills /root/.codex/skills

WORKDIR /app

CMD ["/bin/bash"]
