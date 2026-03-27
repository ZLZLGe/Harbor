FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y python3 python3-pip

WORKDIR /root

COPY recovered_artifact_scan.stl /root/
COPY salvage_density_reference.md /root/

# Copy skills to agent-specific locations
# codex-hide-skill COPY skills /root/.claude/skills
# codex-hide-skill COPY skills /root/.codex/skills
# codex-hide-skill COPY skills /root/.opencode/skill
# codex-hide-skill COPY skills /root/.goose/skills
# codex-hide-skill COPY skills /root/.factory/skills
# codex-hide-skill COPY skills /root/.agents/skills
# codex-hide-skill COPY skills /root/.gemini/skills
