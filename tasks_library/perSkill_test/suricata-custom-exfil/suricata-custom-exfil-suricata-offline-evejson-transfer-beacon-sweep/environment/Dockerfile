FROM jasonish/suricata:7.0.11

ENV DEBIAN_FRONTEND=noninteractive

RUN dnf -y install \
    python3 \
    python3-pip \
    jq \
    ca-certificates \
    && dnf clean all \
    && rm -rf /var/cache/dnf

RUN pip3 install --no-cache-dir \
    pytest==8.4.1 \
    scapy==2.5.0

WORKDIR /root

RUN mkdir -p /root/beacon-sweep/pcaps /root/answer
RUN cp /etc/suricata/suricata.yaml /root/beacon-sweep/suricata.yaml

COPY beacon.rules /root/beacon-sweep/beacon.rules
COPY generate_beacon_pcaps.py /root/generate_beacon_pcaps.py

RUN python3 /root/generate_beacon_pcaps.py --out /root/beacon-sweep/pcaps \
    && rm /root/generate_beacon_pcaps.py

COPY skills /root/.codex/skills

ENTRYPOINT []
CMD ["bash", "-lc", "sleep infinity"]
