FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages \
    defusedxml==0.7.1 \
    lxml==5.3.0 \
    pytest==8.4.1 \
    six==1.17.0

WORKDIR /root
COPY Case-Study-Credits.pptx /root/
COPY skills /root/.codex/skills
