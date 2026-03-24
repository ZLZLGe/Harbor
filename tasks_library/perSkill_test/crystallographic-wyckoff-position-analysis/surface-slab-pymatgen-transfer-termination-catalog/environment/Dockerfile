FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir \
    pymatgen==2025.10.7

RUN mkdir -p /root/workspace /root/slab_catalog_inputs

COPY FeS2_mp-226.cif /root/slab_catalog_inputs/FeS2_mp-226.cif
COPY HgSe_mp-1018722.cif /root/slab_catalog_inputs/HgSe_mp-1018722.cif
COPY slab_requests.json /root/slab_catalog_inputs/slab_requests.json

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
