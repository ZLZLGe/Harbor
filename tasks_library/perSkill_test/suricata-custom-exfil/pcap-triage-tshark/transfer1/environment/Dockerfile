FROM jasonish/suricata:7.0.11

ENV PYTHONUNBUFFERED=1

RUN dnf -y install \
    python3-pip \
    wireshark-cli \
    ca-certificates \
    && dnf clean all \
    && rm -rf /var/cache/dnf

RUN pip3 install --no-cache-dir scapy==2.5.0

WORKDIR /root

COPY pcap_http_utils.py /root/pcap_http_utils.py
COPY make_task_data.py /root/make_task_data.py
RUN python3 /root/make_task_data.py && rm /root/make_task_data.py

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills

ENTRYPOINT []
CMD ["bash", "-lc", "sleep infinity"]
