FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y python3 python3-pip

WORKDIR /root

# Copy problem files
COPY foundry_scan.stl /root/
COPY alloy_density_table.md /root/
COPY feedstock_cost_table.md /root/

# Copy skills to agent-specific locations
# Claude Code
# codex-hide-skill COPY skills /root/.claude/skills
# Codex
# codex-hide-skill COPY skills /root/.codex/skills
# OpenCode - singular "skill"
# codex-hide-skill COPY skills /root/.opencode/skill
# Goose
# codex-hide-skill COPY skills /root/.goose/skills
# Factory
# codex-hide-skill COPY skills /root/.factory/skills
# Portable agents format (Goose, Amp)
# codex-hide-skill COPY skills /root/.agents/skills
# Gemini
# codex-hide-skill COPY skills /root/.gemini/skills
