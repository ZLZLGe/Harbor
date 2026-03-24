FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    poppler-utils \
  && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    pandas==2.2.3 \
    pypdf==5.4.0 \
    pytest==8.4.1

RUN mkdir -p /app/data /app/output

COPY skills /root/.codex/skills
COPY data/ /app/data/

CMD ["/bin/bash"]
