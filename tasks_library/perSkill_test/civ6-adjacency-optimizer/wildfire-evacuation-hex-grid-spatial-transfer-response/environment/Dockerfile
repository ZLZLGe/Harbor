FROM python:3.11-slim

WORKDIR /root

COPY data/ /data/
COPY skills /root/.codex/skills

RUN pip install --no-cache-dir pytest==8.3.4 && mkdir -p /output

CMD ["/bin/bash"]
