# Dockerfile for structure normalization transfer task
FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir \
    pymatgen==2025.10.7

RUN mkdir -p /root/workspace /root/inputs

COPY *.cif /root/inputs/
COPY *.vasp /root/inputs/

# Copy skills to agent-specific locations
# codex-hide-skill COPY skills /root/.claude/skills
# codex-hide-skill COPY skills /root/.codex/skills
# codex-hide-skill COPY skills /root/.opencode/skill
# codex-hide-skill COPY skills /root/.goose/skills
# codex-hide-skill COPY skills /root/.factory/skills
# codex-hide-skill COPY skills /root/.agents/skills
# codex-hide-skill COPY skills /root/.gemini/skills
# codex-hide-skill COPY skills /etc/claude-code/.claude/skills

WORKDIR /root

CMD ["/bin/bash"]
