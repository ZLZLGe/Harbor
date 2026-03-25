FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN pip install --no-cache-dir \
    numpy==1.26.4 \
    pandas==2.2.3 \
    scipy==1.13.1 \
    astropy==6.1.7 \
    lightkurve==2.5.1 \
    pytest==8.4.1

WORKDIR /root

COPY data /root/data
COPY skills /root/.codex/skills
