FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        tshark \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    pytest==8.4.1 \
    scapy==2.5.0

WORKDIR /workspace

RUN mkdir -p /workspace/inputs /workspace/outputs

COPY generate_tls_handshake_mix.py /tmp/generate_tls_handshake_mix.py
RUN python3 /tmp/generate_tls_handshake_mix.py /workspace/inputs/tls_handshake_mix.pcap \
    && rm /tmp/generate_tls_handshake_mix.py

COPY skills /root/.codex/skills

ENTRYPOINT []
CMD ["bash", "-lc", "sleep infinity"]
