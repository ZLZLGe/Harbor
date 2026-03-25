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

COPY heater_model.json /root/heater_model.json
COPY oven_cases.json /root/oven_cases.json
COPY thermal_oven_env.py /root/thermal_oven_env.py
COPY heater_controller_scaffold.py /root/heater_controller_scaffold.py
COPY skills /root/.codex/skills

CMD ["/bin/bash"]
