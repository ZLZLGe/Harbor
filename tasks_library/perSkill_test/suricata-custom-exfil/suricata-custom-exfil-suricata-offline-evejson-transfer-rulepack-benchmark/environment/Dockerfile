FROM jasonish/suricata:7.0.11

ENV DEBIAN_FRONTEND=noninteractive

RUN dnf -y install \
    python3 \
    python3-pip \
    ca-certificates \
    && dnf clean all \
    && rm -rf /var/cache/dnf

RUN pip3 install --no-cache-dir \
    pytest==8.4.1 \
    scapy==2.5.0

WORKDIR /root

RUN mkdir -p /root/rulepack-benchmark/pcaps /root/rulepack-benchmark/rulepacks /root/answer

COPY suricata.yaml /root/rulepack-benchmark/suricata.yaml
COPY labels.json /root/rulepack-benchmark/labels.json
COPY candidate-blue.rules /root/rulepack-benchmark/rulepacks/candidate-blue.rules
COPY candidate-red.rules /root/rulepack-benchmark/rulepacks/candidate-red.rules
COPY generate_tls_benchmark_pcaps.py /root/generate_tls_benchmark_pcaps.py

RUN python3 /root/generate_tls_benchmark_pcaps.py --out /root/rulepack-benchmark/pcaps \
    && rm /root/generate_tls_benchmark_pcaps.py

COPY skills /root/.codex/skills

ENTRYPOINT []
CMD ["bash", "-lc", "sleep infinity"]
