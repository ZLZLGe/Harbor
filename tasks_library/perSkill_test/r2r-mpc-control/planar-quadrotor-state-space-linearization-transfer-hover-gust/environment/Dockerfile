FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

COPY quadrotor_case.json /root/quadrotor_case.json
COPY planar_quadrotor.py /root/planar_quadrotor.py
COPY skills /root/.codex/skills

RUN pip3 install --break-system-packages \
    numpy==1.26.4

CMD ["/bin/bash"]
