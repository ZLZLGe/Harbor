FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

COPY reheat_commissioning_case.json /root/reheat_commissioning_case.json
COPY reheat_loop_simulator.py /root/reheat_loop_simulator.py
COPY skills /root/.codex/skills

RUN pip3 install --break-system-packages \
    pytest==8.4.1

CMD ["/bin/bash"]
