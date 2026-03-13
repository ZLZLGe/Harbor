FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv

WORKDIR /root

RUN pip3 install --break-system-packages \
    numpy==1.26.4 \
    pandas==2.2.2 \
    pyyaml==6.0.1 \
    pytest==8.4.1 \
    pytest-json-ctrf==0.3.5

COPY descent_vehicle.yaml /root/descent_vehicle.yaml
COPY grade_profile.csv /root/grade_profile.csv
COPY target_speed_profile.csv /root/target_speed_profile.csv

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills
