# Dockerfile for coordination signature analysis task
FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir \
    pymatgen==2025.10.7

RUN mkdir -p /root/workspace /root/coordination_inputs

COPY Al2O3_mp-7048.cif /root/coordination_inputs/
COPY FeS2_mp-226.cif /root/coordination_inputs/
COPY HgSe_mp-1018722.cif /root/coordination_inputs/
COPY SiO2_mp-7000.cif /root/coordination_inputs/
COPY coordination_targets.json /root/coordination_targets.json

# Copy skills to agent-specific locations
COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills
COPY skills /etc/claude-code/.claude/skills

WORKDIR /root

CMD ["/bin/bash"]
