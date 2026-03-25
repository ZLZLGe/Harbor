FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

COPY greenhouse_humidity_case.json /root/greenhouse_humidity_case.json
COPY summary_minutes.csv /root/summary_minutes.csv
COPY skills /root/.codex/skills

RUN pip3 install --break-system-packages pytest==8.4.1

CMD ["/bin/bash"]
