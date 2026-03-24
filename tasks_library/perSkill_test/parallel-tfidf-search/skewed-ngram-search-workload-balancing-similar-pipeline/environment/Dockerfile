FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

RUN mkdir -p /root/workspace
COPY workspace/ngram_support_corpus.py /root/workspace/ngram_support_corpus.py
COPY workspace/sequential_ngram.py /root/workspace/sequential_ngram.py
COPY skills /root/.codex/skills

CMD ["python", "--version"]
