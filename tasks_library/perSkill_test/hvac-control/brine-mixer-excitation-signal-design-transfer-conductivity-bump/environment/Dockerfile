FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages pytest==8.4.1

WORKDIR /root

COPY brine_mixer_simulator.py /root/brine_mixer_simulator.py
COPY mixing_station_profile.json /root/mixing_station_profile.json
COPY skills /root/.codex/skills

CMD ["/bin/bash"]
