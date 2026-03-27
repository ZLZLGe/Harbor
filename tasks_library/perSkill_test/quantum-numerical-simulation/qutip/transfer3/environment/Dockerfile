FROM python:3.11-slim

ENV PIP_NO_CACHE_DIR=1

WORKDIR /root

COPY gate_cases.json /root/gate_cases.json
COPY gate_audit_lab.py /root/gate_audit_lab.py

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills

RUN python -m pip install --no-cache-dir \
    numpy==1.26.4 \
    scipy==1.12.0 \
    qutip==5.0.4 \
    pytest==8.4.1 \
    pytest-json-ctrf==0.3.5

CMD ["/bin/bash"]
