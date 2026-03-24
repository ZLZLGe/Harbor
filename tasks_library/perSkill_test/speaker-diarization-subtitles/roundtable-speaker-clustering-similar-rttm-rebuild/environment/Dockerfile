FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --break-system-packages --no-cache-dir \
    numpy==1.26.4 \
    scipy==1.11.4 \
    scikit-learn==1.5.2 \
    pytest==8.4.1 \
    pyannote.core==5.0.0 \
    pyannote.metrics==3.2.1

WORKDIR /app/workspace
COPY panel_segments.json /root/panel_segments.json

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills
