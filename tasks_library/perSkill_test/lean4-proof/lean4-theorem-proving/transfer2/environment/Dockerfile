FROM python:3.11-slim

WORKDIR /app/workspace

COPY workspace /app/workspace

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills

RUN cp -a /app/workspace /app/baseline \
 && chown -R root:root /app/baseline \
 && chmod -R a-w /app/baseline \
 && mkdir -p /logs/verifier

CMD ["/bin/sh"]
