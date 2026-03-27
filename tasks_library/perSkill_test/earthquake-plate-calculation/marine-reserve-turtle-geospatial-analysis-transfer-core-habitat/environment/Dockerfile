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

COPY pelagia_turtle_pings.csv /root/pelagia_turtle_pings.csv
COPY pelagia_marine_reserve.geojson /root/pelagia_marine_reserve.geojson
COPY pelagia_reserve_boundary.geojson /root/pelagia_reserve_boundary.geojson

# codex-hide-skill COPY skills /root/.claude/skills
# codex-hide-skill COPY skills /root/.codex/skills
# codex-hide-skill COPY skills /root/.opencode/skill
# codex-hide-skill COPY skills /root/.goose/skills
# codex-hide-skill COPY skills /root/.factory/skills
# codex-hide-skill COPY skills /root/.agents/skills
# codex-hide-skill COPY skills /root/.gemini/skills
