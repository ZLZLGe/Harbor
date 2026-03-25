FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        tshark \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --no-cache-dir \
    pytest==8.4.1 \
    scapy==2.5.0

WORKDIR /workspace

COPY generate_irc_mix_pcap.py /tmp/generate_irc_mix_pcap.py
RUN mkdir -p /workspace/inputs /workspace/outputs \
    && python /tmp/generate_irc_mix_pcap.py /workspace/inputs/irc_mix.pcap \
    && rm /tmp/generate_irc_mix_pcap.py

COPY skills /root/.codex/skills

ENTRYPOINT []
CMD ["bash", "-lc", "sleep infinity"]
