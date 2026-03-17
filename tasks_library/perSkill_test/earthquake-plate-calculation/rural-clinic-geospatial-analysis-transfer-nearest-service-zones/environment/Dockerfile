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

COPY county_boundaries.geojson /root/county_boundaries.geojson
COPY rural_clinics.geojson /root/rural_clinics.geojson
COPY rural_settlements.geojson /root/rural_settlements.geojson

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills
