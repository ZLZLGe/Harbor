FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /root

RUN pip install --no-cache-dir openpyxl==3.1.5 pytest==8.4.1

RUN mkdir -p /root/data /root/results
COPY data/training_block_experiment.xlsx /root/data/training_block_experiment.xlsx

COPY skills /root/.codex/skills
