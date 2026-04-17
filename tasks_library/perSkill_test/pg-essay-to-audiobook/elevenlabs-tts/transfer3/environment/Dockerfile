FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /root

COPY data /root/data

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills

ENTRYPOINT []
CMD ["bash", "-lc", "sleep infinity"]
