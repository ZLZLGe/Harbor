FROM python:3.12-slim

ENV PATH="/app/bin:${PATH}"
WORKDIR /app/repo

COPY bin /app/bin
COPY bin /usr/local/bin
COPY ci-logs /app/ci-logs
COPY repo /app/repo
COPY skills /root/.claude/skills
COPY skills /etc/claude-code/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills

RUN chmod +x /app/bin/pnpm /app/bin/curl /app/bin/lsof /usr/local/bin/pnpm /usr/local/bin/curl /usr/local/bin/lsof
