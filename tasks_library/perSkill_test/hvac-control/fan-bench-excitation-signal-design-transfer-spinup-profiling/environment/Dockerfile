FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages \
    numpy==1.26.4 \
    pytest==8.4.1

WORKDIR /root

COPY fan_spinup_simulator.py /root/fan_spinup_simulator.py
COPY fan_bench_profile.json /root/fan_bench_profile.json
COPY skills /root/.codex/skills

CMD ["/bin/bash"]
