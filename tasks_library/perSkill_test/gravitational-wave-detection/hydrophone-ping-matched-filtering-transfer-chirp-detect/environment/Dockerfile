FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1

RUN pip install numpy==2.1.3 pytest==8.4.1

WORKDIR /root

COPY data /root/data
COPY skills /root/.codex/skills
