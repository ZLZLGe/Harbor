FROM jasonish/suricata:7.0.11

ENV DEBIAN_FRONTEND=noninteractive

RUN dnf -y install \
    python3 \
    python3-pip \
    jq \
    ca-certificates

RUN pip3 install --no-cache-dir \
    pytest==8.4.1 \
    scapy==2.5.0

WORKDIR /root

RUN mkdir -p /root/lateral-timeline /root/answer

COPY suricata.yaml /root/lateral-timeline/suricata.yaml
COPY lateral.rules /root/lateral-timeline/lateral.rules
COPY generate_lateral_timeline_assets.py /root/generate_lateral_timeline_assets.py

RUN python3 /root/generate_lateral_timeline_assets.py \
    --pcap /root/lateral-timeline/ops-east-long.pcap

COPY skills /root/.codex/skills

ENTRYPOINT []
CMD ["bash", "-lc", "sleep infinity"]
