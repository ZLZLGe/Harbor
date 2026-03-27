FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /root

COPY data /root/data
COPY tools /root/tools

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills

RUN chmod +x /root/tools/offline_tts.py

ENTRYPOINT []
CMD ["bash", "-lc", "sleep infinity"]
