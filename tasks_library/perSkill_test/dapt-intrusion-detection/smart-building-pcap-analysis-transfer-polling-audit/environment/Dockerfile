FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    wget \
    unzip \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages \
    pyyaml==6.0.2 \
    scapy==2.5.0

WORKDIR /root

# Synthetic smart-building polling capture and blank YAML template.
COPY build_smart_building_pcap.py /tmp/build_smart_building_pcap.py
COPY smart_building_polling_audit_template.yaml /root/smart_building_polling_audit.yaml
RUN python3 /tmp/build_smart_building_pcap.py /root/smart_building_devices.pcap

# Copy skills
COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills
COPY skills /root/skills

RUN python3 - <<'PY'
import sys
from scapy.all import rdpcap

sys.path.insert(0, "/root/skills/pcap-analysis")
import pcap_utils

assert callable(rdpcap)
assert callable(pcap_utils.load_packets)
PY
