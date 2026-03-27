FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

RUN pip install --no-cache-dir \
    opencv-python-headless==4.12.0.88 \
    pytest==8.4.1 \
    pytest-json-ctrf==0.3.5

WORKDIR /root

COPY coin.png /root/coin.png
COPY enemy.png /root/enemy.png
COPY turtle.png /root/turtle.png
COPY image_manifest.json /root/image_manifest.json
COPY skills /root/skills
COPY skills /root/.codex/skills
