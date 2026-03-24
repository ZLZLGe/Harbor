FROM gcr.io/oss-fuzz-base/base-builder-python

RUN apt-get update && apt-get install -y tree

WORKDIR /app
COPY packaging_backend_repo /app/packaging_backend_repo

# Copy skills to ALL agent paths
COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills
