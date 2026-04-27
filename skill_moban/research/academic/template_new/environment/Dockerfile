FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    bash \
    ca-certificates \
    curl \
    jq \
    python3 \
    python3-pip \
    python-is-python3 \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages --no-cache-dir \
    pytest==8.3.4 \
    requests==2.32.3 \
    bibtexparser==1.4.2

WORKDIR /root

COPY research_packet /root/research_packet
COPY evidence_snapshot.json /root/research_packet/evidence_snapshot.json
COPY evidence_gateway.py /opt/evidence_gateway.py

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills

RUN printf '%s\n' \
    'if ! curl -fsS http://127.0.0.1:8765/health >/dev/null 2>&1; then' \
    '  python /opt/evidence_gateway.py >/tmp/evidence_gateway.log 2>&1 &' \
    '  sleep 0.2' \
    'fi' \
    > /etc/profile.d/evidence_gateway.sh
