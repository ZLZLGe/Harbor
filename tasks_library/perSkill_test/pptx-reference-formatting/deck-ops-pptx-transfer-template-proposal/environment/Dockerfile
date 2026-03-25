FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

RUN pip install \
    lxml==5.3.0 \
    Pillow==10.4.0 \
    PyYAML==6.0.2 \
    pytest==8.4.1 \
    python-pptx==1.0.2 \
    six==1.17.0

WORKDIR /root

COPY proposal_brief.yaml /root/proposal_brief.yaml
COPY build_seed_assets.py /root/build_seed_assets.py
RUN python /root/build_seed_assets.py && rm /root/build_seed_assets.py

COPY skills /root/.codex/skills
