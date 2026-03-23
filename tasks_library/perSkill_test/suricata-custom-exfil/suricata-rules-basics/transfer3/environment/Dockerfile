FROM harbor-suricata-local-probe:latest

RUN python3 -m ensurepip --upgrade \
    && pip3 install \
        pytest==8.4.1 \
        pytest-json-ctrf==0.3.5 \
        scapy==2.5.0

WORKDIR /root

COPY suricata.yaml /root/suricata.yaml
COPY starter.rules /root/transfer3.rules
COPY generate_training_pcaps.py /root/generate_training_pcaps.py
RUN mkdir -p /root/pcaps \
    && python3 /root/generate_training_pcaps.py --out /root/pcaps \
    && rm /root/generate_training_pcaps.py

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills
COPY skills /root/skills

ENTRYPOINT []
CMD ["bash", "-lc", "sleep infinity"]
