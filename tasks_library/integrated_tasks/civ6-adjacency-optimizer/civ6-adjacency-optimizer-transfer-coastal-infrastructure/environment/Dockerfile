FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /root

# Copy only the assets needed for this derived task.
COPY data/ /data/

# Copy skills to all agent reference locations.
COPY skills /root/skills

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills

RUN mkdir -p /output

CMD ["/bin/bash"]
