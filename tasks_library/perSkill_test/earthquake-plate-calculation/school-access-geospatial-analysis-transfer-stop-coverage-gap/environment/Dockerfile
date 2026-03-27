FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    curl \
    git \
    vim \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    pandas==2.2.3 \
    numpy==1.26.4 \
    geopandas==1.0.1 \
    shapely==2.0.6 \
    pyproj==3.7.0

WORKDIR /root

COPY school_locations.csv /root/school_locations.csv
COPY bus_stops.csv /root/bus_stops.csv

# Copy skills to agent-specific locations
# Claude Code
# codex-hide-skill COPY skills /root/.claude/skills
# Codex
# codex-hide-skill COPY skills /root/.codex/skills
# OpenCode
# codex-hide-skill COPY skills /root/.opencode/skill
# codex-hide-skill COPY skills /root/.goose/skills
# codex-hide-skill COPY skills /root/.factory/skills
# Goose/Amp (portable agents format)
# codex-hide-skill COPY skills /root/.agents/skills
# Gemini
# codex-hide-skill COPY skills /root/.gemini/skills
